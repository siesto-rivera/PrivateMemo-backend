from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Category, Memo
from .serializers import CategorySerializer, MemoSerializer


PROTECTED_CATEGORY_NAMES = {"미분류"}


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.name in PROTECTED_CATEGORY_NAMES:
            return Response(
                {"detail": f"기본 카테고리 '{instance.name}'는 삭제할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        new_name = request.data.get("name")
        if (
            instance.name in PROTECTED_CATEGORY_NAMES
            and new_name is not None
            and new_name != instance.name
        ):
            return Response(
                {"detail": f"기본 카테고리 '{instance.name}'의 이름은 변경할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)


class MemoViewSet(viewsets.ModelViewSet):
    serializer_class = MemoSerializer

    def get_queryset(self):
        return Memo.objects.select_related("category").filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
