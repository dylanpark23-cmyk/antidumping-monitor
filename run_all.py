"""전체 실행: 소스별 수집 → 사이트 생성 → 메일 알림.
한 소스가 실패해도 나머지는 계속 진행합니다."""
import os
import traceback

from collectors import cn_mofcom, eu_tron, in_dgtr, kr_ktc, trade_data, us_federal_register
from collectors.common import load_config
from notify.email_new import send
from web.build_site import build

SOURCES = [
    ("미국 Federal Register", us_federal_register.run),
    ("한국 무역위원회", kr_ktc.run),
    ("중국 상무부", cn_mofcom.run),
    ("EU", eu_tron.run),
    ("인도 DGTR", in_dgtr.run),
]


def main() -> None:
    cfg = load_config()
    fresh, failed = [], []
    for name, fn in SOURCES:
        try:
            res = fn()
            if res["first_run"]:
                print(f"[메일] {name}: 최초 수집이라 과거 공고는 알림 생략")
                continue
            by_id = {r["id"]: r for r in res["records"]}
            fresh += [by_id[i] for i in res["new_ids"] if i in by_id]
        except Exception as e:
            from collectors.common import load_store
            # 무역위원회는 해외 서버 접속이 막혀 있어 기존(브라우저로 받아둔) 데이터를 유지
            if not (name == "한국 무역위원회" and load_store("kr_ktc.json")):
                failed.append(name)
            print(f"[오류] {name} 수집 실패: {e}")
            traceback.print_exc()
    try:
        trade_data.run()
    except Exception as e:
        print(f"[오류] DATA 수집 실패: {e}")
    build(failed_sources=failed)
    send(fresh, only_watched=cfg.get("email_only_watched", True), site_url=os.environ.get("SITE_URL", ""))


if __name__ == "__main__":
    main()
