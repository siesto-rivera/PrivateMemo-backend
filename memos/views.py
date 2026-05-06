from rest_framework import status, viewsets
from rest_framework.decorators import action
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
        # Reassign memos to 미분류 instead of cascade-deleting them.
        # Cascade still happens on User.delete() (the FK is on_delete=CASCADE),
        # but in that case both source and 미분류 are being deleted anyway.
        uncategorized, _ = Category.objects.get_or_create(
            user=request.user,
            name="미분류",
            defaults={"emoji": "📁"},
        )
        Memo.objects.filter(category=instance).update(category=uncategorized)
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

    @action(detail=True, methods=["post"])
    def merge(self, request, pk=None):
        source = self.get_object()
        if source.name in PROTECTED_CATEGORY_NAMES:
            return Response(
                {"detail": f"기본 카테고리 '{source.name}'는 통합할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        target_id = request.data.get("target_id")
        if not target_id:
            return Response(
                {"detail": "target_id가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            target = Category.objects.get(user=request.user, pk=target_id)
        except Category.DoesNotExist:
            return Response(
                {"detail": "대상 카테고리를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if source.pk == target.pk:
            return Response(
                {"detail": "같은 카테고리로 통합할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        moved = Memo.objects.filter(category=source).update(category=target)
        source.delete()
        return Response(
            {
                "detail": f"{moved}개의 메모가 '{target.name}'(으)로 이동되었습니다.",
                "moved": moved,
                "target": CategorySerializer(target).data,
            }
        )


class MemoViewSet(viewsets.ModelViewSet):
    serializer_class = MemoSerializer

    def get_queryset(self):
        return Memo.objects.select_related("category").filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
