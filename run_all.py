"""전체 실행: 수집 → 사이트 생성 → 메일 알림.  (앞으로 무역위·관세청·Comtrade 수집기도 여기에 추가)"""
import os

from collectors import us_federal_register
from collectors.common import load_config
from notify.email_new import send
from web.build_site import build


def main() -> None:
    cfg = load_config()
    res = us_federal_register.run()
    build()
    if res["first_run"]:
        print("[메일] 최초 실행이라 과거 공고는 메일로 보내지 않음")
        return
    by_id = {r["id"]: r for r in res["records"]}
    send([by_id[i] for i in res["new_ids"] if i in by_id],
         only_watched=cfg.get("email_only_watched", True),
         site_url=os.environ.get("SITE_URL", ""))


if __name__ == "__main__":
    main()
