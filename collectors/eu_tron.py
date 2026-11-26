"""EU 집행위원회 무역구제 공고(TRON notices API) 수집 → data/eu_tron.json"""
import datetime as dt
import re

from collectors.common import get_json, merge_store, targets_of

API = "https://tron.trade.ec.europa.eu/investigations/api/eucase/notices/{y}/{y}"
CASE = "https://tron.trade.ec.europa.eu/investigations/case-view?caseId={id}"
STORE = "eu_tron.json"


def stage_of(kind: str, text: str) -> tuple:
    k, t = (kind or "").lower(), (text or "").lower()
    review = "review" in t or "expiry" in t
    if "initiation" in k or "notice of initiation" in t:
        if "expiry review" in t:
            return "일몰재심 개시", 2
        if review:
            return "재심 개시", 2
        if "circumvention" in t:
            return "우회 조사 개시", 2
        return "신규 조사 개시(EU)", 1
    if "provisional" in k or "provisional" in t:
        return "예비판정(잠정관세)", 2
    if "definitive" in k or "imposing a definitive" in t:
        return "최종판정(확정관세)", 2
    if "termination" in k or "terminating" in t:
        return "조사 종료", 2
    if "expiry" in k or "impending expiry" in t:
        return "일몰 예고", 3
    if "review" in k:
        return "재심", 2
    return "기타", 3


def remedy_of(case_no: str, text: str) -> str:
    t = (text or "").lower()
    if (case_no or "").startswith("SAFE") or "safeguard" in t:
        return "SG"
    if "anti-subsidy" in t or "countervailing" in t or (case_no or "").startswith("AS"):
        return "CVD"
    return "AD"


def run() -> dict:
    today = dt.date.today()
    years = [today.year] + ([today.year - 1] if today.month <= 3 else [])
    recs = []
    for y in years:
        data = get_json(API.format(y=y))
        for n in data if isinstance(data, list) else []:
            text = re.sub(r"\s+", " ", n.get("contents") or "").strip()
            kind = n.get("typeOfPublication") or ""
            if re.search(r"questionnaire|sampling form", text + kind, re.I):
                continue
            countries = n.get("countryList") or []
            erga = any("erga omnes" in c.lower() for c in countries)
            stage, prio = stage_of(kind, text)
            ms = n.get("publicationDate")
            date = dt.datetime.utcfromtimestamp(ms / 1000 + 7200).date().isoformat() if ms else None
            watch = (["Korea"] if any("korea" in c.lower() for c in countries) else []) + (["Erga Omnes(전 세계)"] if erga else [])
            recs.append({
                "id": f"EU-{n.get('publicationId')}", "source": "EU-TRON", "authority": "EU", "status": "게재",
                "agency": "EU 집행위", "title": text[:400], "product": (n.get("shortName") or "").strip(),
                "countries": countries, "targets": [] if erga else targets_of(countries),
                "stage": stage, "priority": prio, "remedy": remedy_of(n.get("caseNumber"), text),
                "case_numbers": [n.get("caseNumber")] if n.get("caseNumber") else [], "watch": watch,
                "snippets": [], "abstract": f"구분: {kind}", "publication_date": date,
                "html_url": CASE.format(id=n.get("caseID")) if n.get("caseID") else n.get("url"),
                "pdf_url": n.get("url"),
            })
    res = merge_store(STORE, recs)
    print(f"[EU] 신규 {len(res['new_ids'])}건, 누적 {len(res['records'])}건")
    return res


if __name__ == "__main__":
    run()
