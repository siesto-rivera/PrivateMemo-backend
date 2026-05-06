# PrivateMemoBackend

[지극히 사적인 메모장](https://github.com/siesto-rivera/PrivateMemo)의 Django 백엔드.
class-mobile (Expo) / class-web (Next.js) 두 클라이언트가 공유하는 REST API.

## 스택

- Python 3.14
- Django 6.0
- Django REST Framework 3.17
- SimpleJWT 5.5 (인증)
- MariaDB (cafe24 호스팅)

## 설치

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`mysqlclient` 빌드에는 시스템 라이브러리가 필요합니다. macOS:

```bash
brew install mysql-client
PKG_CONFIG_PATH="/usr/local/opt/mysql-client/lib/pkgconfig:$PKG_CONFIG_PATH" pip install mysqlclient
```

## 환경 변수

루트에 `.env` 파일을 만들어 주세요. `.env.example`을 참고:

```
MYSQL_HOST=...
MYSQL_DB=...
MYSQL_USERNAME=...
MYSQL_PASSWORD=...
MYSQL_PORT=3306    # optional, 기본값 3306
```

## 실행

```bash
# 마이그레이션 (최초 1회 + 모델 변경 시)
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser

# 개발 서버 (로컬 전용)
python manage.py runserver 127.0.0.1:8001

# 개발 서버 (LAN 접속 허용 — 모바일 실기기 테스트 시)
python manage.py runserver 0.0.0.0:8001
```

`ALLOWED_HOSTS`에 LAN IP를 추가해야 합니다 (`config/settings.py`).

어드민: <http://127.0.0.1:8001/admin/>

## API

기본 경로: `/api/`. 인증 필요한 엔드포인트는 `Authorization: Bearer <access>` 헤더 필요.

### 인증 — `/api/auth/`

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/signup/` | `{email, name, password}` | `{user, access, refresh}` |
| POST | `/login/` | `{email, password}` | `{access, refresh}` |
| POST | `/refresh/` | `{refresh}` | `{access}` |
| GET / PATCH | `/me/` | (PATCH 시 `{name}` 등) | `{id, email, name, date_joined}` |

토큰 수명: access **60분**, refresh **14일**.

### 카테고리 — `/api/categories/`

| Method | Path | Body |
|---|---|---|
| GET | `/` | (목록) |
| POST | `/` | `{name, emoji?}` |
| PATCH | `/{id}/` | `{name?, emoji?}` |
| DELETE | `/{id}/` | — |

`미분류` 카테고리는 이름 변경/삭제 불가 (400 응답).

### 메모 — `/api/memos/`

| Method | Path | Body |
|---|---|---|
| GET | `/` | (현재 유저의 메모 목록) |
| POST | `/` | `{category_name, memo, alarm_date?, tag?}` |
| PATCH | `/{id}/` | (필드 부분 업데이트) |
| DELETE | `/{id}/` | — |

응답 형태:
```json
{
  "id": 1,
  "category_name": "영화",
  "memo": "...",
  "alarm_date": "2026-06-15T09:00:00+09:00",
  "tag": ["SF", "재관람"],
  "createDate": "2026-05-06T11:00:00+09:00"
}
```

## 데이터 모델

- `accounts.User` — 이메일 기반 로그인 (`USERNAME_FIELD='email'`), `name` 필드, `AbstractBaseUser` 기반.
- `memos.Category` — `(user, name)` unique, `emoji` 포함. 신규 가입 시 11개 기본 카테고리 자동 시드 (시그널).
- `memos.Memo` — `user` FK (CASCADE), `category` FK (CASCADE — 카테고리 삭제 시 메모도 함께), `tag`는 `JSONField`.

유저별로 메모/카테고리 격리. 다른 유저의 데이터는 API에서 보이지 않음.

## 시드 카테고리

신규 가입자에게 자동 생성되는 카테고리 (`memos/signals.py`):

`📁 미분류` `🎬 영화` `📚 책` `🏠 주소` `🍜 맛집` `📍 장소` `🔑 비번` `🚗 차량관리` `🏍️ 오토바이 관리` `🛠️ 집관리` `💳 계좌 이벤트`

## CORS

class-web (Next.js dev: `localhost:3000`), class-mobile (Expo dev: `:8081`, `:19006`)을 위한 origin이 `config/settings.py`에 화이트리스트로 등록되어 있습니다. LAN IP (`192.168.*`, `10.*`)에서의 접근은 정규식으로 허용.

## 운영 시 고려사항

- **타임존**: `USE_TZ=True`, `TIME_ZONE='Asia/Seoul'`. cafe24 MariaDB의 `mysql.time_zone_name` 테이블이 비어있어 `CONVERT_TZ()`를 사용하는 쿼리(`Trunc()` 등)는 실패합니다. 그래서 `MemoAdmin`에는 `date_hierarchy`를 쓰지 않습니다.
- **utf8mb4**: DB charset을 `utf8mb4`로 ALTER 함 (이모지 저장 가능). 신규 테이블도 자동으로 utf8mb4.
- **SECRET_KEY / DEBUG**: 운영 배포 전 환경변수로 분리 + `DEBUG=False` + `ALLOWED_HOSTS` 정리 필수.

## 라이선스

CC BY-NC 4.0 (PrivateMemo와 동일).
