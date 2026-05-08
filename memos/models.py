from django.conf import settings
from django.db import models


class Category(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=64)
    emoji = models.CharField(max_length=8, blank=True, default="")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_category_name_per_user"
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.user.email}] {self.name}"


class Memo(models.Model):
    REPEAT_CHOICES = [
        ("none", "None"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memos",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="memos",
    )
    memo = models.TextField()
    alarm_date = models.DateTimeField(null=True, blank=True)
    schedule_date = models.DateField(null=True, blank=True, db_index=True)
    repeat = models.CharField(
        max_length=10, choices=REPEAT_CHOICES, default="none"
    )
    tag = models.JSONField(default=list, blank=True)
    # Asset IDs from the user's photo library (device-specific, e.g. iOS PhotoKit IDs).
    # Image binaries themselves stay in the user's Photos app — we only keep references.
    images = models.JSONField(default=list, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-create_date"]

    def __str__(self) -> str:
        return f"[{self.category.name}] {self.memo[:30]}"
