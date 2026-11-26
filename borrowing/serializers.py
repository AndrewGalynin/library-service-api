from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from book.models import Book
from book.serializers import BookSerializer
from borrowing.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
        )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("id", "book", "expected_return_date")

    def validate_expected_return_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "Expected return date cannot be in the past."
            )
        return value

    def validate_book(self, value):
        if value.inventory <= 0:
            raise serializers.ValidationError(
                "This book is currently out of stock."
            )
        return value

    def create(self, validated_data):
        with transaction.atomic():
            book = Book.objects.select_for_update().get(
                pk=validated_data["book"].pk
            )
            if book.inventory <= 0:
                raise serializers.ValidationError(
                    {"book": "This book is currently out of stock."}
                )
            book.inventory -= 1
            book.save(update_fields=["inventory"])
            return Borrowing.objects.create(**validated_data)

    def to_representation(self, instance):
        return BorrowingSerializer(instance, context=self.context).data
