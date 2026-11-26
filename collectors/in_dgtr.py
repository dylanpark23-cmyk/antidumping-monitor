"""인도 DGTR 반덤핑·상계관세·세이프가드 사건 타임라인 수집 → data/in_dgtr.json"""
import datetime as dt
import re
import time

from collectors.common import get_text, merge_store, strip_tags, targets_of

BASE = "https://www.dgtr.gov.in"
STORE = "in_dgtr.json"
LISTS = [("/en/anti-dumping-investigation-in-india", "AD", 3),
         ("/en/countervailing-duty-investigation", "CVD", 1),
         ("/en/safe-guard-investigation-in-india", "SG", 1)]


def parse_list(html_text: str) -> list:
    out = []
    for block in re.findall(r'<div class="investigation">(.*?)</div>\s*</div>', html_text, re.S):
        a = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not a:
            continue
        status = re.search(r'<span class="status">(.*?)</span>', block, re.S)
        country = re.search(r"Country:\s*(.*?)</span>", block, re.S)
        procs = re.findall(r'<span class="proceeding">(.*?)</span>', block, re.S)
        out.append({"href": a.group(1) if a.group(1).startswith("http") else BASE + a.group(1),
                    "title": strip_tags(a.group(2)), "status": strip_tags(status.group(1)) if status else "",
                    "country": strip_tags(country.group(1)) if country else "",
                    "proceeding": " / ".join(strip_tags(p) for p in procs)})
    return out


def parse_case(html_text: str) -> dict:
    prod = re.search(r"Product\s*:\s*(.*?)<", html_text, re.S)
    rows = []
    tbody = re.search(r"<tbody>(.*?)</tbody>", html_text, re.S)
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbody.group(1) if tbody else "", re.S):
        cells = re.findall(r"<td([^>]*)>(.*?)</td>", tr, re.S)
        if len(cells) < 4:
            continue
        rid = re.search(r'id="(\d+)"', cells[1][0])
        link = re.search(r'href="([^"]+)"', cells[2][1])
        d = re.search(r"(\d{2})/(\d{2})/(\d{4})", strip_tags(cells[3][1]))
        rows.append({"rid": rid.group(1) if rid else None, "title": strip_tags(cells[1][1]),
                     "pdf": link.group(1) if link else None,
                     "date": f"{d.group(3)}-{d.group(2)}-{d.group(1)}" if d else None})
    return {"product": strip_tags(prod.group(1)) if prod else "", "rows": rows}


def split_countries(s: str) -> list:
    return [c.strip() for c in re.split(r",|\band\b|&", s) if c.strip()]


def stage_of(row_title: str, proceeding: str) -> tuple:
    t, p = row_title.lower(), proceeding.lower()
    if "initiation" in t:
        if "sunset" in p:
            return "일몰재심 개시", 2
        if "mid term" in p or "midterm" in p:
            return "중간재심 개시", 2
        if "anti-circumvention" in p or "circumvention" in p:
            return "우회 조사 개시", 2
        if "review" in p:
            return "재심 개시", 2
        return "신규 조사 개시(인도)", 1
    if "preliminary" in t or "provisional" in t:
        return "예비판정", 2
    if "final finding" in t:
        return "최종판정", 2
    if "customs notification" in t or "notification of ministry of finance" in t or "duty" in t and "notification" in t:
        return "관세부과 명령", 2
    if "termination" in t:
        return "조사 종료", 2
    if "hearing" in t or "extension" in t or "corrigendum" in t:
        return "일정·공지", 3
    return "기타", 3


def run(max_cases: int = 60, days: int = 365) -> dict:
    cases = []
    for path, remedy, pages in LISTS:
        for page in range(pages):
            items = parse_list(get_text(f"{BASE}{path}" + (f"?page={page}" if page else "")))
            if not items:
                break
            cases += [dict(i, remedy=remedy) for i in items]
            time.sleep(1)
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    recs = []
    for c in cases[:max_cases]:
        try:
            detail = parse_case(get_text(c["href"]))
        except Exception as e:
            print(f"[인도] 사건 페이지 실패 {c['href']}: {e}")
            continue
        countries = split_countries(c["country"])
        for r in detail["rows"]:
            if not r["rid"] or not r["date"] or r["date"] < cutoff:
                continue
            stage, prio = stage_of(r["title"], c["proceeding"])
            recs.append({
                "id": f"DGTR-{r['rid']}", "source": "IN-DGTR", "authority": "IN", "status": "게재",
                "agency": "인도 DGTR", "title": f"{r['title']} — {c['title']}",
                "product": detail["product"] or c["title"], "countries": countries,
                "targets": targets_of(countries), "stage": stage, "priority": prio, "remedy": c["remedy"],
                "case_numbers": [], "watch": ["Korea"] if re.search(r"korea", c["country"], re.I) else [],
                "snippets": [], "abstract": f"{c['proceeding']} · {c['status']}",
                "publication_date": r["date"], "html_url": c["href"], "pdf_url": r["pdf"],
            })
        time.sleep(1)
    res = merge_store(STORE, recs)
    print(f"[인도 DGTR] 사건 {min(len(cases), max_cases)}개 확인, 신규 공고 {len(res['new_ids'])}건, 누적 {len(res['records'])}건")
    return res


if __name__ == "__main__":
    run()
