from django.utils import timezone

from borrowing.models import Borrowing
from notification.telegram import send_telegram_message


def send_telegram_notification(message: str) -> bool:
    return send_telegram_message(message)


def check_overdue_borrowings() -> None:
    today = timezone.now().date()
    overdue_borrowings = Borrowing.objects.select_related(
        "book", "user"
    ).filter(
        expected_return_date__lte=today,
        actual_return_date__isnull=True,
    )

    if not overdue_borrowings.exists():
        send_telegram_message("No borrowings overdue today!")
        return

    lines = ["<b>Overdue Borrowings Report:</b>\n"]
    for borrowing in overdue_borrowings:
        lines.append(
            f"• ID #{borrowing.id}: <b>{borrowing.book.title}</b> "
            f"(User: {borrowing.user.email}, "
            f"Expected return: {borrowing.expected_return_date})"
        )

    send_telegram_message("\n".join(lines))
