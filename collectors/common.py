"""공통 유틸: HTTP 요청, 설정/데이터 파일 읽기·쓰기."""
import json
import time
import urllib.request
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
