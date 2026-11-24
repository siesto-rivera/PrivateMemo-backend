"""ERROR 로그를 텔레그램 알림 방으로 보내는 logging 핸들러 (2026-11-24, 모든 Django 사이트 공통 사본).

- env TELEGRAM_ALERT_BOT_TOKEN · TELEGRAM_ALERT_CHAT_ID 가 없으면 아무것도 하지 않는다(로컬·테스트는 조용하다).
- 요청을 느리게 하지 않는다: 백그라운드 스레드로 보내고 5초 안에 응답이 없으면 버린다. 실패해도 예외를 내지 않는다.
- 같은 오류(로거·예외 종류·발생 위치가 같은 것)는 프로세스마다 10분에 한 번만 보낸다(알림 폭주 방지).
- 개인정보를 줄인다: 요청 본문·쿠키·헤더는 보내지 않는다. 주소의 긴 토큰 같은 조각(20자 이상)은 가린다.
  예외 메시지는 300자까지만 보낸다(DB 오류 메시지에 값이 섞일 수 있다).

settings.LOGGING 에서 쓰는 법:
    "handlers": {"telegram": {"class": "<앱>.telegram_alert.TelegramAlertHandler", "site": "academy"}},
    "root": {"handlers": ["console", "telegram"], "level": "INFO"},
"""
import hashlib
import json
import logging
import os
import re
import threading
import time
import traceback
import urllib.request

_TOKENISH = re.compile(r"[A-Za-z0-9_\-:=]{20,}")
# 보내지 않는 로거: 허용하지 않은 Host 로 들어온 요청은 인터넷 스캐너가 수시로 보내 ERROR 로 남는다(400 으로 이미 막힌다)
IGNORE_LOGGERS = ("django.security.DisallowedHost",)


class TelegramAlertHandler(logging.Handler):
    def __init__(self, site="", min_interval=600):
        super().__init__(level=logging.ERROR)
        self.site = site or os.environ.get("ALERT_SITE_NAME", "")
        self.min_interval = min_interval
        self._last = {}
        self._lock = threading.Lock()

    def _signature(self, record):
        exc = record.exc_info[1] if record.exc_info else None
        where = f"{record.pathname}:{record.lineno}"
        if record.exc_info and record.exc_info[2]:
            tb = traceback.extract_tb(record.exc_info[2])
            if tb:
                where = f"{tb[-1].filename}:{tb[-1].lineno}"
        raw = f"{record.name}|{type(exc).__name__ if exc else record.msg}|{where}"
        return hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()

    def format_alert(self, record):
        exc = record.exc_info[1] if record.exc_info else None
        req = getattr(record, "request", None)
        if req is not None and hasattr(req, "path"):
            where = f"{getattr(req, 'method', '')} {_TOKENISH.sub('…', req.path)}"
        else:
            where = record.name
        head = f"🔴 [{self.site or '?'}] {where}"
        if exc is not None:
            body = f"{type(exc).__name__}: {str(exc)[:300]}"
            tb = traceback.extract_tb(record.exc_info[2]) if record.exc_info[2] else []
            # 마지막 '우리 코드' 줄을 보여 준다(site-packages 는 건너뛴다)
            ours = [f for f in tb if "site-packages" not in f.filename] or tb
            loc = f"{ours[-1].filename.split('/usr/src/app/')[-1]}:{ours[-1].lineno} {ours[-1].name}" if ours else ""
        else:
            body = str(record.getMessage())[:300]
            loc = f"{record.module}:{record.lineno}"
        return "\n".join(x for x in (head, body, loc) if x)

    def emit(self, record):
        token = os.environ.get("TELEGRAM_ALERT_BOT_TOKEN", "").strip()
        chat = os.environ.get("TELEGRAM_ALERT_CHAT_ID", "").strip()
        if not token or not chat:
            return
        if record.name.startswith(IGNORE_LOGGERS):
            return
        try:
            key = self._signature(record)
            now = time.monotonic()
            with self._lock:
                if now - self._last.get(key, -1e9) < self.min_interval:
                    return
                self._last[key] = now
            text = self.format_alert(record)
            threading.Thread(target=_send, args=(token, chat, text), daemon=True).start()
        except Exception:  # 알림 때문에 앱이 죽으면 안 된다
            pass


def _send(token, chat, text):
    base = os.environ.get("TELEGRAM_ALERT_API_BASE", "https://api.telegram.org")
    try:
        data = json.dumps({"chat_id": chat, "text": text[:3500], "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(f"{base}/bot{token}/sendMessage", data=data,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass
