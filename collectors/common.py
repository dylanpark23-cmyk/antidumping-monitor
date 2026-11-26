"""공통 유틸: HTTP 요청, 설정/데이터 파일 읽기·쓰기."""
import json
import time
import urllib.parse
import urllib.request
import re
import html as _html
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
UA = "AntidumpingHub/1.0 (trade remedy monitoring; contact via GitHub repo)"


class RateLimited(RuntimeError):
    """서버가 HTTP 429(요청 과다)를 돌려줌."""


def _get(url: str, retries: int = 3, timeout: int = 60) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:  # 요청 과다: 재시도하지 않고 바로 알림 (호출한 쪽에서 중단)
                raise RateLimited(url) from e
            if 400 <= e.code < 500:
                break
            time.sleep(2 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"요청 실패: {url} ({last})")


def post_form(url: str, data: dict, timeout: int = 20) -> str:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def get_json(url: str) -> dict:
    return json.loads(_get(url).decode("utf-8"))


def get_text(url: str) -> str:
    return _get(url).decode("utf-8", errors="replace")


def load_config() -> dict:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def load_store(name: str) -> list:
    p = DATA_DIR / name
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def save_store(name: str, records: list) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / name).write_text(
        json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8"
    )


# ---------------------------------------------------------------- 공통 도우미
def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


_KR = re.compile(r"korea|한국|대한민국|韩国", re.I)
_CN = re.compile(r"china|중국|中国", re.I)
_US = re.compile(r"united states|\busa\b|미국|美国", re.I)
_TW = re.compile(r"taiwan|chinese taipei|대만|台湾", re.I)


def norm_country(name: str) -> str:
    """국가명(영/한/중) → KR / CN / US / OT"""
    n = name or ""
    if _KR.search(n):
        return "KR"
    if _TW.search(n):
        return "OT"
    if _CN.search(n):
        return "CN"
    if _US.search(n):
        return "US"
    return "OT"


def targets_of(countries: list) -> list:
    return sorted({norm_country(c) for c in countries if c})


def merge_store(name: str, recs: list, update: bool = True) -> dict:
    """id 기준으로 누적 저장. 반환: new_ids, first_run, records"""
    import datetime as _dt
    store = {r["id"]: r for r in load_store(name)}
    first = not store
    now = _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    new_ids = []
    for r in recs:
        old = store.get(r["id"])
        if old is None:
            r.setdefault("first_seen", now)
            store[r["id"]] = r
            new_ids.append(r["id"])
        elif update:
            r["first_seen"] = old.get("first_seen", now)
            store[r["id"]] = {**old, **r}
    records = sorted(store.values(), key=lambda r: (r.get("publication_date") or "", r["id"]), reverse=True)
    save_store(name, records)
    return {"new_ids": new_ids, "first_run": first, "records": records}
