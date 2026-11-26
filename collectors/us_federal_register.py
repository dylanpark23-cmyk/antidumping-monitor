"""미국 Federal Register 무역구제 공고 수집기.

- 상무부 ITA + 국제무역위원회 ITC 공고 중 반덤핑/상계관세/세이프가드 관련만 수집
- 정식 게재 전날 올라오는 Public Inspection(게재예정) 공고도 수집
- 제목·사건번호(A-580-xxx 등)·본문을 확인해 한국(또는 config의 감시 대상) 관련 여부 표시
- 결과: data/us_fr.json  (document_number 기준 누적·중복 제거)
"""
import datetime as dt
import re
import sys
import time
import urllib.parse

from collectors.common import get_json, get_text, load_config, load_store, save_store

API = "https://www.federalregister.gov/api/v1"
STORE = "us_fr.json"
AGENCIES = {
    "international-trade-administration": "상무부(ITA)",
    "international-trade-commission": "ITC",
}
FIELDS = [
    "title", "type", "abstract", "action", "document_number", "html_url",
    "pdf_url", "publication_date", "agencies", "docket_ids", "raw_text_url",
]
RELEVANT = re.compile(
    r"antidumping|anti-dumping|countervailing|less[- ]than[- ]fair[- ]value|"
    r"five-year|sunset review|administrative review|scope ruling|circumvention|"
    r"safeguard|section 201|global safeguard|AD/CVD",
    re.I,
)
CASE_NO = re.compile(r"\b[AC]-\d{3}-\d{3}\b")
ITC_NO = re.compile(r"\b(?:701|731)-TA-\d{2,4}\b|\bTA-201-\d{2,4}\b")


# ---------------------------------------------------------------- 분류
STAGES = [  # (정규식, 단계명, 중요도 1=최고)
    (r"initiation of less[- ]than[- ]fair[- ]value investigation|initiation of countervailing duty investigation", "신규 조사 개시(상무부)", 1),
    (r"institution of (?:anti-?dumping|countervailing)|institution of .*investigations?.*preliminary", "신규 조사 개시(ITC)", 1),
    (r"petition", "신규 제소(청원)", 1),
    (r"preliminary affirmative determination|preliminary negative determination|preliminary determination", "예비판정", 2),
    (r"final affirmative determination|final negative determination|final determination", "최종판정", 2),
    (r"antidumping duty order|countervailing duty order|amended .*order", "관세부과 명령", 2),
    (r"preliminary results of .*administrative review", "연례재심 예비결과", 2),
    (r"final results of .*administrative review", "연례재심 최종결과", 2),
    (r"initiation of .*administrative review", "연례재심 개시", 2),
    (r"opportunity to request administrative review", "연례재심 신청기회", 3),
    (r"five-year|sunset", "일몰재심", 2),
    (r"changed circumstances", "상황변경재심", 2),
    (r"circumvention", "우회 조사", 2),
    (r"scope", "범위 판정", 3),
    (r"new shipper", "신규수출자 재심", 3),
    (r"rescission|partial rescission", "재심 철회", 3),
    (r"safeguard|section 201", "세이프가드", 2),
    (r"revocation", "명령 철회", 2),
    (r"meeting|hearing|scheduling", "일정·청문회", 3),
]


def classify(title: str) -> tuple:
    t = title or ""
    for pat, name, prio in STAGES:
        if re.search(pat, t, re.I):
            return name, prio
    return "기타", 3


def remedy_type(text: str) -> str:
    t = (text or "").lower()
    ad = bool(re.search(r"antidumping|anti-dumping|less[- ]than[- ]fair", t))
    cvd = "countervailing" in t
    if "safeguard" in t or "section 201" in t:
        return "SG"
    if ad and cvd:
        return "AD/CVD"
    return "AD" if ad else ("CVD" if cvd else "-")


def parse_title(title: str) -> tuple:
    """'Certain Steel Nails From the Republic of Korea and Taiwan: Final ...' → (품목, [국가])"""
    m = re.match(r"(.+?)\s+[Ff]rom\s+(.+?)(?::|;|$)", title or "")
    if not m:
        return "", []
    product = m.group(1).strip()
    raw = re.sub(r"\bthe\s+", "", m.group(2), flags=re.I)
    parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", raw)
    countries = [p.strip(" .") for p in parts if p.strip(" .")]
    return product, countries


# ---------------------------------------------------------------- 감시 대상 판정
def watch_hits(text: str, cfg: dict) -> list:
    hits = []
    for c in cfg.get("watch_countries", []):
        if re.search(re.escape(c), text or "", re.I):
            hits.append(c)
    for code in cfg.get("watch_country_codes", []):
        if re.search(rf"\b[AC]-{code}-\d{{3}}\b", text or ""):
            hits.append(f"사건번호 {code}")
    for co in cfg.get("watch_companies", []):
        if co and re.search(re.escape(co), text or "", re.I):
            hits.append(co)
    return sorted(set(hits))


def fulltext_snippets(raw: str, cfg: dict, limit: int = 25) -> list:
    """본문에서 감시 대상이 나오는 줄 + 아래 2줄을 발췌 (연례재심 개시 공고처럼 여러 나라 사건이 묶인 공고용)."""
    lines = [l.strip() for l in raw.splitlines()]
    pats = [re.escape(x) for x in cfg.get("watch_countries", []) + cfg.get("watch_companies", []) if x]
    pats += [rf"\b[AC]-{c}-\d{{3}}\b" for c in cfg.get("watch_country_codes", [])]
    if not pats:
        return []
    rx = re.compile("|".join(pats), re.I)
    out, used = [], set()
    for i, l in enumerate(lines):
        if i in used or not rx.search(l):
            continue
        chunk = " ".join(x for x in lines[i:i + 3] if x)
        used.update(range(i, i + 3))
        out.append(re.sub(r"\s+", " ", chunk)[:400])
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- API 호출
def fetch_published(since: str) -> list:
    params = [("per_page", "1000"), ("order", "newest"),
              ("conditions[publication_date][gte]", since)]
    params += [("conditions[agencies][]", a) for a in AGENCIES]
    params += [("fields[]", f) for f in FIELDS]
    url = f"{API}/documents.json?{urllib.parse.urlencode(params)}"
    out = []
    while url:
        page = get_json(url)
        out.extend(page.get("results") or [])
        url = page.get("next_page_url")
        if url:
            time.sleep(0.5)
    return out


def fetch_public_inspection() -> list:
    page = get_json(f"{API}/public-inspection-documents/current.json")
    out = []
    for d in page.get("results") or []:
        names = " ".join((a.get("name") or "") + " " + (a.get("slug") or "") for a in d.get("agencies") or [])
        if re.search(r"international trade (administration|commission)|international-trade-(administration|commission)", names, re.I):
            out.append(d)
    return out


def agency_label(doc: dict) -> str:
    for a in doc.get("agencies") or []:
        slug = a.get("slug") or ""
        if slug in AGENCIES:
            return AGENCIES[slug]
        name = (a.get("name") or "").lower()
        if "trade commission" in name:
            return "ITC"
        if "trade administration" in name:
            return "상무부(ITA)"
    return "기타"


# ---------------------------------------------------------------- 레코드 만들기
def to_record(doc: dict, status: str, cfg: dict, now: str) -> dict:
    title = doc.get("title") or ""
    text = " ".join(filter(None, [title, doc.get("abstract"), doc.get("action"),
                                  " ".join(doc.get("docket_ids") or [])]))
    stage, prio = classify(title)
    product, countries = parse_title(title)
    return {
        "id": doc.get("document_number"),
        "source": "US-FR",
        "status": status,  # "게재" | "게재예정"
        "agency": agency_label(doc),
        "title": title,
        "product": product,
        "countries": countries,
        "stage": stage,
        "priority": prio,
        "remedy": remedy_type(text),
        "case_numbers": sorted(set(CASE_NO.findall(text) + ITC_NO.findall(text))),
        "watch": watch_hits(text, cfg),
        "snippets": [],
        "abstract": (doc.get("abstract") or "")[:1200],
        "publication_date": doc.get("publication_date"),
        "html_url": doc.get("html_url"),
        "pdf_url": doc.get("pdf_url"),
        "raw_text_url": doc.get("raw_text_url"),
        "first_seen": now,
        "fulltext_checked": False,
    }


def run(today: dt.date = None) -> dict:
    cfg = load_config()
    today = today or dt.date.today()
    now = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    store = {r["id"]: r for r in load_store(STORE)}
    first = not store
    days = cfg.get("first_run_days", 120) if first else cfg.get("regular_lookback_days", 10)
    since = (today - dt.timedelta(days=days)).isoformat()

    incoming = []
    try:
        for d in fetch_public_inspection():
            incoming.append(("게재예정", d))
    except Exception as e:  # 게재예정 실패해도 본 수집은 계속
        print(f"[경고] Public Inspection 수집 실패: {e}", file=sys.stderr)
    for d in fetch_published(since):
        incoming.append(("게재", d))

    new_ids, updated = [], 0
    for status, d in incoming:
        doc_id = d.get("document_number")
        blob = " ".join(filter(None, [d.get("title"), d.get("abstract"), d.get("action")]))
        if not doc_id or not RELEVANT.search(blob):
            continue
        rec = to_record(d, status, cfg, now)
        old = store.get(doc_id)
        if old is None:
            store[doc_id] = rec
            new_ids.append(doc_id)
        elif old["status"] == "게재예정" and status == "게재":
            rec["first_seen"] = old["first_seen"]
            rec["watch"] = sorted(set(rec["watch"]) | set(old.get("watch", [])))
            store[doc_id] = rec
            updated += 1

    # 제목에 감시 대상이 없는 공고는 본문까지 확인 (여러 국가 묶음 공고 대응)
    budget = cfg.get("max_fulltext_checks_per_run", 80)
    for rec in sorted(store.values(), key=lambda r: r.get("publication_date") or "", reverse=True):
        if budget <= 0:
            break
        if rec["fulltext_checked"] or rec["status"] != "게재" or not rec.get("raw_text_url"):
            continue
        try:
            raw = get_text(rec["raw_text_url"])
            hits = watch_hits(raw, cfg)
            if hits:
                rec["watch"] = sorted(set(rec["watch"]) | set(hits))
                rec["snippets"] = fulltext_snippets(raw, cfg)
                rec["case_numbers"] = sorted(set(rec["case_numbers"]) | set(CASE_NO.findall(raw)))[:40]
            rec["fulltext_checked"] = True
        except Exception as e:
            print(f"[경고] 본문 확인 실패 {rec['id']}: {e}", file=sys.stderr)
        budget -= 1
        time.sleep(0.4)

    records = sorted(store.values(), key=lambda r: (r.get("publication_date") or "9999", r["id"]), reverse=True)
    save_store(STORE, records)
    print(f"[미국 FR] 신규 {len(new_ids)}건, 게재 전환 {updated}건, 누적 {len(records)}건 (최초실행={first})")
    return {"new_ids": new_ids, "first_run": first, "records": records}


if __name__ == "__main__":
    run()
