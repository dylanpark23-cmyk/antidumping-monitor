"""한국무역협회(KITA) 수입규제DB — 전 세계 대(對)한국 수입규제(반덤핑·상계관세·세이프가드·우회수출) → data/kita_import_reg.json

KITA 가 44개국의 한국 피제소 사건을 사건 단위로 정리해 둔 DB 라서,
튀르키예·브라질·호주·인도네시아 등 개별 수집기가 없는 나라도 모두 잡힙니다.
- 목록: importRegulationCardList.do (POST, 100건씩)
- 상세: importRegulationCardDetail.do?tirId=... (진행 단계·피제소국·HS코드·관련 링크)
최근갱신일이 바뀐 사건만 상세를 다시 읽어요.
해외 서버(GitHub) 접속이 막히면 기존 데이터(브라우저로 받아둔 것)를 그대로 둡니다.
"""
import datetime as dt
import re
import time

from collectors.common import load_store, merge_store, post_form, strip_tags, targets_of, get_text

BASE = "https://www.kita.net/importRegulation/importRegulation/"
LIST_URL = BASE + "importRegulationCardList.do"
DETAIL_URL = BASE + "importRegulationCardDetail.do?tirId="
STORE = "kita_import_reg.json"
MAX_DETAILS = 120          # 한 번 실행에 상세를 읽을 최대 건수 (최초 실행은 전체)

COUNTRY_CODE = {
    "미국": "US", "중국": "CN", "EU": "EU", "인도": "IN", "튀르키예": "TR", "브라질": "BR", "호주": "AU",
    "캐나다": "CA", "인도네시아": "ID", "말레이시아": "MY", "태국": "TH", "필리핀": "PH", "베트남": "VN",
    "일본": "JP", "대만": "TW", "남아프리카공화국": "ZA", "이집트": "EG", "우크라이나": "UA", "러시아": "RU",
    "EAEU": "EAEU", "GCC": "GCC", "파키스탄": "PK", "멕시코": "MX", "아르헨티나": "AR", "콜롬비아": "CO",
    "칠레": "CL", "영국": "GB", "뉴질랜드": "NZ", "마다가스카르": "MG", "모로코": "MA", "사우디아라비아": "SA",
    "요르단": "JO", "튀니지": "TN", "짐바브웨": "ZW", "잠비아": "ZM", "우즈베키스탄": "UZ", "에콰도르": "EC",
    "코스타리카": "CR", "과테말라": "GT", "파나마": "PA", "이스라엘": "IL", "키르기스스탄": "KG",
    "도미니카공화국": "DO", "바레인": "BH", "페루": "PE", "카자흐스탄": "KZ", "아르메니아": "AM",
}
REMEDY = {"반덤핑": "AD", "상계관세": "CVD", "세이프가드": "SG", "우회수출": "우회수출"}
STATUS_STAGE = {"조사중": "조사 진행 중", "규제중": "규제 중(조치 시행)", "조사종료": "조사 종료", "규제종료": "규제 종료"}


def _date(s: str) -> str:
    s = (s or "").strip().replace(".", "-")
    return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else ""


def parse_list(html_text: str) -> list:
    out = []
    for chunk in html_text.split('<div class="cate')[1:]:
        m = re.search(r"goDetailPage\('([^']+)'\)\"\s*title=\"([^\"]*)\"", chunk)
        if not m:
            continue
        country = re.search(r'class="caption[^"]*">\s*([^<]+?)\s*</span>', chunk)
        t = strip_tags(chunk)
        g = lambda pat: (re.search(pat, t) or [None, ""])[1]
        out.append({
            "tid": m.group(1), "title": strip_tags(m.group(2)), "country": country.group(1).strip() if country else "",
            "init": _date(g(r"조사개시일\s*:\s*([\d.]+)")), "upd": _date(g(r"최근갱신일\s*:\s*([\d.]+)")),
            "type": g(r"규제유형\s*:\s*(\S+)"), "status": g(r"규제상태\s*:\s*(\S+)"),
        })
    return out


def parse_detail(html_text: str) -> dict:
    i = html_text.find("경과 및 특이사항</h3>")
    j = html_text.find("알아두세요", i)
    sec = html_text[i:j] if i >= 0 else ""
    steps = []
    for blk in re.findall(r'<div class="subject[^"]*"[^>]*>\s*([^<]+?)\s*</div>', sec):
        m = re.match(r"(.+?)\((\d{4}\.\d{2}\.\d{2})\)$", blk.strip())
        if m:
            steps.append((m.group(1).strip(), _date(m.group(2))))
    link = re.search(r'href="(https?://[^"]+)"[^>]*>\s*관련 링크', sec)
    victims = re.search(r"피제소국\s*:\s*([^<]+)", sec)
    k = html_text.find("<p>HS코드</p>")
    hs_part = html_text[k:html_text.find("</td>", k)] if k >= 0 else ""
    hs = re.findall(r'class="badge radius">\s*([\d.]+)\s*<', hs_part)
    return {
        "steps": steps,
        "link": link.group(1) if link else "",
        "victims": [v.strip() for v in victims.group(1).split(",") if v.strip()] if victims else [],
        "hs": hs[:12],
    }


def to_record(row: dict, det: dict) -> dict:
    steps = det.get("steps") or []
    latest = steps[0] if steps else None
    stage = f"{latest[0]}({latest[1]})" if latest else STATUS_STAGE.get(row["status"], row["status"])
    if row["status"] in ("조사종료", "규제종료"):
        stage = f"{STATUS_STAGE[row['status']]} · {stage}" if latest else stage
    if row["status"] == "조사중" and (not latest or "개시" in latest[0]):
        priority = 1
    elif re.search(r"재심|재조사|연장", stage):
        priority = 2
    else:
        priority = 3
    victims = det.get("victims") or ["한국"]
    code = COUNTRY_CODE.get(row["country"], "OT")
    hs = det.get("hs") or []
    return {
        "id": "KITA-" + row["tid"], "source": "KITA 수입규제DB", "authority": code,
        "agency": f"{row['country']} 조사당국", "status": row["status"],
        "title": f"[{row['country']}] {row['title']}", "product": row["title"],
        "countries": victims, "targets": sorted(set(targets_of(victims)) | {"KR"}),
        "stage": stage, "priority": priority, "remedy": REMEDY.get(row["type"], row["type"]),
        "case_numbers": [], "watch": ["Korea"],
        "snippets": [],
        "abstract": " · ".join(x for x in [
            ("진행: " + " → ".join(f"{s}({d})" for s, d in reversed(steps))) if steps else "",
            f"조사개시일 {row['init']}" if row["init"] else "",
            ("피제소국: " + ", ".join(victims)) if det.get("victims") else "",
            ("HS " + ", ".join(hs)) if hs else ""] if x),
        "publication_date": row["upd"] or row["init"], "init_date": row["init"],
        "html_url": DETAIL_URL + row["tid"], "pdf_url": det.get("link", ""),
    }


def run() -> dict:
    rows, page = [], 1
    while page <= 20:
        try:
            html_text = post_form(LIST_URL, {
                "pageIndex": str(page), "pageUnit": "100", "tirId": "", "expandSeachYn": "N",
                "searchContinentNm": "", "searchContinentCd": "", "searchCountryNm": "", "searchCountryCd": "",
                "searchContinent": "", "searchNation": "", "searchRestGubun": "", "searchItemGubun": "",
                "searchKeywordType": "", "searchKeyword": "", "searchDateType": "1",
                "searchStartDate": "", "searchEndDate": "", "searchOrder": "1",
            }, timeout=30)
        except (TimeoutError, OSError) as e:
            raise RuntimeError("KITA 사이트가 해외 서버(GitHub) 접속을 막는 것으로 보여요. "
                               "기존 데이터는 그대로 유지됩니다. (" + str(e) + ")") from None
        got = parse_list(html_text)
        rows += got
        if len(got) < 100:
            break
        page += 1
        time.sleep(0.5)
    if not rows:
        raise RuntimeError("KITA 수입규제DB 목록을 읽지 못했어요 (페이지 구조 변경 가능)")

    old = {r["id"]: r for r in load_store(STORE)}
    first = not old
    recs, fetched = [], 0
    for row in rows:
        rid = "KITA-" + row["tid"]
        prev = old.get(rid)
        same = prev and prev.get("publication_date") == (row["upd"] or row["init"]) and prev.get("status") == row["status"]
        if same and prev.get("detail_ok"):
            continue                      # 바뀐 게 없으면 그대로
        if same and fetched >= MAX_DETAILS:
            continue
        det = {}
        if first or fetched < MAX_DETAILS:
            try:
                det = parse_detail(get_text(DETAIL_URL + row["tid"]))
                fetched += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"[KITA] 상세 실패 {row['tid']}: {e}")
        rec = to_record(row, det)
        rec["detail_ok"] = bool(det.get("steps") or det.get("victims"))
        recs.append(rec)
    res = merge_store(STORE, recs)
    print(f"[KITA 수입규제DB] 목록 {len(rows)}건, 갱신 {len(recs)}건(상세 {fetched}), 신규 {len(res['new_ids'])}건")
    return res
