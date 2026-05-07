from rest_framework import serializers

from .models import Category, Memo


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "emoji"]


class UserScopedCategoryField(serializers.SlugRelatedField):
    """SlugRelatedField that only accepts categories owned by the request user."""

    def get_queryset(self):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return Category.objects.none()
        return Category.objects.filter(user=request.user)


class MemoSerializer(serializers.ModelSerializer):
    category_name = UserScopedCategoryField(source="category", slug_field="name")
    createDate = serializers.DateTimeField(source="create_date", read_only=True)

    class Meta:
        model = Memo
        fields = [
            "id",
            "category_name",
            "memo",
            "alarm_date",
            "repeat",
            "tag",
            "createDate",
        ]
