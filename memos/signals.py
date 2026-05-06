from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


DEFAULT_CATEGORIES = [
    ("미분류", "📁"),
    ("영화", "🎬"),
    ("책", "📚"),
    ("주소", "🏠"),
    ("맛집", "🍜"),
    ("장소", "📍"),
    ("비번", "🔑"),
    ("차량관리", "🚗"),
    ("오토바이 관리", "🏍️"),
    ("집관리", "🛠️"),
    ("계좌 이벤트", "💳"),
]


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def seed_default_categories(sender, instance, created, **kwargs):
    if not created:
        return
    from .models import Category

    Category.objects.bulk_create(
        [
            Category(user=instance, name=name, emoji=emoji)
            for name, emoji in DEFAULT_CATEGORIES
        ]
    )
