from django.db import migrations


def seed_uncategorized(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Category = apps.get_model("memos", "Category")
    for user in User.objects.all():
        Category.objects.get_or_create(
            user=user,
            name="미분류",
            defaults={"emoji": "📁"},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("memos", "0002_alter_memo_category"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_uncategorized, reverse_code=migrations.RunPython.noop),
    ]
