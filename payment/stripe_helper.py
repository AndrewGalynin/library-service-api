from decimal import Decimal
import stripe
from django.conf import settings
from django.urls import reverse

from borrowing.models import Borrowing
from payment.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY


def calculate_borrowing_amount(borrowing: Borrowing) -> Decimal:
    days = (borrowing.expected_return_date - borrowing.borrow_date).days
    days = max(days, 1)
    return Decimal(days) * borrowing.book.daily_fee


def calculate_fine_amount(borrowing: Borrowing) -> Decimal:
    if (
        not borrowing.actual_return_date
        or borrowing.actual_return_date <= borrowing.expected_return_date
    ):
        return Decimal("0.00")

    overdue_days = (
        borrowing.actual_return_date - borrowing.expected_return_date
    ).days
    return (
        Decimal(overdue_days)
        * borrowing.book.daily_fee
        * Decimal(settings.FINE_MULTIPLIER)
    )


def create_stripe_session(
    borrowing: Borrowing,
    request,
    payment_type: str = Payment.Type.PAYMENT,
) -> Payment:
    if payment_type == Payment.Type.FINE:
        amount = calculate_fine_amount(borrowing)
        product_name = f"Overdue Fine: {borrowing.book.title}"
    else:
        amount = calculate_borrowing_amount(borrowing)
        product_name = f"Book Borrowing: {borrowing.book.title}"

    success_url = (
        request.build_absolute_uri(reverse("payment:payment-success"))
        + "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = request.build_absolute_uri(reverse("payment:payment-cancel"))

    checkout_session = stripe.checkout.Session.create(
        allowed_payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": product_name,
                    },
                    "unit_amount": int(amount * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return Payment.objects.create(
        status=Payment.Status.PENDING,
        type=payment_type,
        borrowing=borrowing,
        session_url=checkout_session.url,
        session_id=checkout_session.id,
        money_to_pay=amount,
    )
