from django.apps import AppConfig


class MemosConfig(AppConfig):
    name = "memos"

    def ready(self):
        from . import signals  # noqa: F401
