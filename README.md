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

| Method | Path | Body | 비고 |
|---|---|---|---|
| GET | `/` | — | (목록) |
| POST | `/` | `{name, emoji?}` | |
| PATCH | `/{id}/` | `{name?, emoji?}` | |
| DELETE | `/{id}/` | — | 메모를 `미분류`로 이동 후 카테고리 삭제 (cascade 아님) |
| POST | `/{id}/merge/` | `{target_id}` | 해당 카테고리의 메모를 `target_id` 카테고리로 이동 후 source 삭제 |

`미분류` 카테고리 보호:
- 이름 변경 불가 (400)
- 삭제 불가 (400)
- merge의 source 불가 (400). target은 가능 (다른 카테고리의 메모를 미분류로 옮길 때).

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
- `memos.Category` — `(user, name)` unique, `emoji` 포함. 신규 가입 시 4개 기본 카테고리 자동 시드 (시그널).
- `memos.Memo` — `user` FK (CASCADE), `category` FK (CASCADE), `tag`는 `JSONField`. 카테고리 삭제는 API 단에서 메모를 `미분류`로 이동시킨 뒤 진행되므로 실제로 cascade는 발동하지 않음 (cascade는 유저 탈퇴 시 안전망 역할).

유저별로 메모/카테고리 격리. 다른 유저의 데이터는 API에서 보이지 않음.

## 시드 카테고리

신규 가입자에게 자동 생성되는 카테고리 (`memos/signals.py`):

`📁 미분류` `🎬 영화` `📚 책` `📍 장소`

## CORS

class-web (Next.js dev: `localhost:3000`), class-mobile (Expo dev: `:8081`, `:19006`)을 위한 origin이 `config/settings.py`에 화이트리스트로 등록되어 있습니다. LAN IP (`192.168.*`, `10.*`)에서의 접근은 정규식으로 허용.

## 운영 시 고려사항

- **타임존**: `USE_TZ=True`, `TIME_ZONE='Asia/Seoul'`. cafe24 MariaDB의 `mysql.time_zone_name` 테이블이 비어있어 `CONVERT_TZ()`를 사용하는 쿼리(`Trunc()` 등)는 실패합니다. 그래서 `MemoAdmin`에는 `date_hierarchy`를 쓰지 않습니다.
- **utf8mb4**: DB charset을 `utf8mb4`로 ALTER 함 (이모지 저장 가능). 신규 테이블도 자동으로 utf8mb4.
- **SECRET_KEY / DEBUG**: 운영 배포 전 환경변수로 분리 + `DEBUG=False` + `ALLOWED_HOSTS` 정리 필수.

## 배포 (AWS Lightsail + GitHub Actions)

운영: **AWS Lightsail (Amazon Linux 2023)** + Nginx + Gunicorn + systemd. main 브랜치 push 시 GitHub Actions 가 SSH로 서버에 접속해 자동 배포.

### 구성 요약

```
GitHub Actions  ──ssh──>  Lightsail (54.116.131.130)
  on push:main           - git pull
                         - pip install
                         - migrate
                         - collectstatic
                         - systemctl restart memo-app

Client → Nginx :80 → Gunicorn 127.0.0.1:8001 → Django (memo-app.service)
```

- **앱 디렉토리**: `~/github/memo-app` (ec2-user 홈 안)
- **systemd unit**: `memo-app.service` (`scripts/memo-app.service`)
- **Nginx**: `/etc/nginx/conf.d/memo-app.conf` (`scripts/nginx-memo-app.conf`)

### 1회 서버 부트스트랩

1. **Lightsail 인스턴스에 포트 80 열기** (Networking 탭에서 HTTP 허용).
2. SSH 접속:
   ```bash
   ssh -i ~/nodong1987.pem ec2-user@54.116.131.130
   ```
3. 부트스트랩 다운로드 후 1차 실행 (Python/nginx 설치 + repo clone, .env 부재 안내):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/siesto-rivera/PrivateMemo-backend/main/scripts/bootstrap.sh -o bootstrap.sh
   bash bootstrap.sh
   ```
4. 로컬에서 `.env`를 서버로 SCP (`.env.example` 복사 후 운영용 값 채워서):
   ```bash
   scp -i ~/nodong1987.pem .env ec2-user@54.116.131.130:~/github/memo-app/.env
   ```
   필수 키: `MYSQL_HOST/DB/USERNAME/PASSWORD`, `DJANGO_SECRET_KEY`(강력한 랜덤), `DEBUG=False`, `ALLOWED_HOSTS=54.116.131.130`, `CSRF_TRUSTED_ORIGINS=http://54.116.131.130`.
5. 부트스트랩 재실행 → migrate, collectstatic, systemd 등록, nginx 설정, sudoers 규칙까지 마무리:
   ```bash
   bash bootstrap.sh
   ```
6. 어드민 계정 생성:
   ```bash
   cd ~/github/memo-app && source venv/bin/activate && python manage.py createsuperuser
   ```
7. http://54.116.131.130/admin/ 로그인 확인.

### GitHub Actions Secret 설정

repo 의 Settings → Secrets and variables → Actions 에서:

- `LIGHTSAIL_SSH_KEY` — `nodong1987.pem` 의 **전체 내용**(`-----BEGIN ... -----END`)을 그대로 붙여넣기

또는 gh CLI로:
```bash
gh secret set LIGHTSAIL_SSH_KEY < ~/nodong1987.pem
```

이후 main 브랜치에 push하면 `.github/workflows/deploy.yml`이 발동되어 자동 배포됩니다. 수동 트리거는 Actions 탭에서 "Run workflow" 가능.

### 배포 동작 (`.github/workflows/deploy.yml`)

1. `appleboy/ssh-action`으로 서버 접속
2. `git fetch origin main && git reset --hard origin/main` (로컬 변경 무시, 강제 동기화)
3. `pip install -r requirements.txt`
4. `python manage.py migrate --noinput`
5. `python manage.py collectstatic --noinput`
6. `sudo systemctl restart memo-app` (sudoers에 NOPASSWD 등록되어 있어 비밀번호 없이 실행)
7. `systemctl status` 출력으로 헬스체크

### 운영 시 주의

- `.env` 파일은 절대 커밋하지 마세요 (`.gitignore` 처리됨).
- `DJANGO_SECRET_KEY`는 운영용으로 새로 생성: `python -c "import secrets; print(secrets.token_urlsafe(50))"`.
- `DEBUG=False` 운영에서는 정적 파일을 Nginx가 직접 서빙합니다 (`/static/` 경로). 코드 수정 시 자동 `collectstatic` 됨.
- 로그: `sudo journalctl -u memo-app -f` (gunicorn 액세스/에러), `/var/log/nginx/access.log` (nginx).
- HTTPS 필요해지면 도메인 연결 후 `certbot --nginx`로 Let's Encrypt 인증서 추가 가능.

## 라이선스

CC BY-NC 4.0 (PrivateMemo와 동일).
