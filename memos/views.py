from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
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
        # Default queryset excludes trashed memos.
        return (
            Memo.objects.select_related("category")
            .filter(user=self.request.user, deleted_at__isnull=True)
            .order_by("-create_date")
        )

    def list(self, request, *args, **kwargs):
        # Pagination is opt-in via ?page=N. Without it, return all memos
        # (used by categories/calendar/alarms which need full dataset).
        page_param = request.query_params.get("page")
        if page_param is None:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        try:
            page = int(page_param)
            page_size = int(request.query_params.get("page_size", 30))
        except (TypeError, ValueError):
            return Response(
                {"detail": "page와 page_size는 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = list(queryset[start:end])
        serializer = self.get_serializer(items, many=True)
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "has_next": end < total,
                "results": serializer.data,
            }
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        # Soft delete — move to trash. Use ?force=1 to permanently delete.
        instance = self.get_object()
        if request.query_params.get("force") in ("1", "true", "True"):
            instance.delete()
        else:
            instance.deleted_at = timezone.now()
            instance.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def trash(self, request):
        qs = (
            Memo.objects.select_related("category")
            .filter(user=request.user, deleted_at__isnull=False)
            .order_by("-deleted_at")
        )
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        try:
            memo = Memo.objects.get(
                user=request.user, pk=pk, deleted_at__isnull=False
            )
        except Memo.DoesNotExist:
            return Response(
                {"detail": "휴지통에 없는 메모입니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        memo.deleted_at = None
        memo.save(update_fields=["deleted_at"])
        return Response(self.get_serializer(memo).data)

    @action(detail=False, methods=["post"], url_path="empty_trash")
    def empty_trash(self, request):
        deleted, _ = Memo.objects.filter(
            user=request.user, deleted_at__isnull=False
        ).delete()
        return Response({"deleted": deleted})

    @action(detail=False, methods=["post"], url_path="bulk_import")
    def bulk_import(self, request):
        items = request.data.get("memos")
        if not isinstance(items, list):
            return Response(
                {"detail": "memos 배열이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        auto_create = bool(request.data.get("auto_create_categories", True))

        # Cache and seed missing categories first (one query for the cache).
        cache = {c.name: c for c in Category.objects.filter(user=request.user)}
        wanted_names = {
            (item.get("category_name") or "").strip()
            for item in items
            if isinstance(item, dict) and (item.get("category_name") or "").strip()
        }
        missing = [n for n in wanted_names if n not in cache]
        if missing and auto_create:
            for name in missing:
                cat = Category.objects.create(user=request.user, name=name)
                cache[name] = cat

        imported = 0
        errors = []
        new_memos = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append({"row": i, "message": "각 항목은 객체여야 합니다."})
                continue
            name = (item.get("category_name") or "").strip()
            text = item.get("memo") or ""
            if not name:
                errors.append({"row": i, "message": "category_name이 비어있습니다."})
                continue
            if not text:
                errors.append({"row": i, "message": "memo가 비어있습니다."})
                continue
            cat = cache.get(name)
            if cat is None:
                errors.append({"row": i, "message": f"카테고리 '{name}' 없음"})
                continue
            alarm_raw = item.get("alarm_date")
            alarm_dt = None
            if alarm_raw:
                alarm_dt = parse_datetime(alarm_raw)
                if alarm_dt is None:
                    errors.append(
                        {"row": i, "message": f"alarm_date 형식 오류: {alarm_raw}"}
                    )
                    continue
            schedule_raw = item.get("schedule_date")
            schedule_d = None
            if schedule_raw:
                schedule_d = parse_date(schedule_raw)
                if schedule_d is None:
                    errors.append(
                        {"row": i, "message": f"schedule_date 형식 오류: {schedule_raw}"}
                    )
                    continue
            tag = item.get("tag") or []
            if not isinstance(tag, list):
                tag = []
            images = item.get("images") or []
            if not isinstance(images, list):
                images = []
            repeat = item.get("repeat") or "none"
            if repeat not in dict(Memo.REPEAT_CHOICES):
                repeat = "none"
            new_memos.append(
                Memo(
                    user=request.user,
                    category=cat,
                    memo=text,
                    alarm_date=alarm_dt,
                    schedule_date=schedule_d,
                    repeat=repeat,
                    tag=tag,
                    images=images,
                )
            )
            imported += 1

        if new_memos:
            Memo.objects.bulk_create(new_memos)

        return Response({"imported": imported, "errors": errors})
