from django.contrib import admin

from .models import Category, Memo


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "user", "memo_count")
    list_filter = ("user",)
    search_fields = ("name", "user__email")
    autocomplete_fields = ("user",)

    @admin.display(description="memos")
    def memo_count(self, obj: Category) -> int:
        return obj.memos.count()


@admin.register(Memo)
class MemoAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "short_memo", "alarm_date", "create_date")
    list_filter = ("user", "category")
    search_fields = ("memo", "user__email")
    autocomplete_fields = ("user", "category")
    readonly_fields = ("create_date",)

    @admin.display(description="memo")
    def short_memo(self, obj: Memo) -> str:
        return obj.memo[:40] + ("…" if len(obj.memo) > 40 else "")
