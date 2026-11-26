"""한국 무역위원회(KTC) 무역구제조사 진행·종결 목록 수집 → data/kr_ktc.json"""
import datetime as dt
import re
import time

from collectors.common import merge_store, post_form, strip_tags, targets_of

URL = "https://www.ktc.go.kr/investArticle.do"
STORE = "kr_ktc.json"
TYPES = {"10100001": "AD", "10100003": "CVD"}   # 반덤핑, 보조금
LISTS = [("11", "진행", "https://www.ktc.go.kr/proInvestList.do", 5),
         ("12", "종결", "https://www.ktc.go.kr/comInvestList.do", 3)]


def parse_rows(html_text: str) -> list:
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(cells) < 5:
            continue
        m = re.search(r"viewInvest\('(\d+)'", tr)
        out.append({
            "mid": m.group(1) if m else None,
            "title": strip_tags(cells[0]), "no": strip_tags(cells[1]),
            "product": strip_tags(cells[2]), "date": strip_tags(cells[3]), "step": strip_tags(cells[4]),
        })
    return out


def countries_from_title(title: str) -> list:
    m = re.match(r"(.+?)산\s", title + " ")
    if not m:
        return []
    return [c.strip() for c in re.split(r",|및|와|과|·", m.group(1)) if c.strip()]


def stage_of(title: str, closed: bool) -> tuple:
    if closed:
        return "조사 종결", 3
    if "종료재심" in title:
        return "일몰재심(종료재심사)", 2
    if "중간재심" in title:
        return "중간재심", 2
    if "재심" in title:
        return "재심", 2
    return "신규 조사 개시(무역위)", 1


def run() -> dict:
    recs = []
    for menu, label, page_url, max_pages in LISTS:
        for code, remedy in TYPES.items():
            for page in range(1, max_pages + 1):
                html_text = post_form(URL, {"menuId": menu, "pageIndex": str(page),
                                            "process_step_code": "11000005", "invstg_type_code": code})
                rows = [r for r in parse_rows(html_text) if r["mid"]]
                if not rows:
                    break
                for r in rows:
                    countries = countries_from_title(r["title"])
                    stage, prio = stage_of(r["title"], label == "종결")
                    d = r["date"].replace(".", "-")
                    recs.append({
                        "id": f"KTC-{r['mid']}", "source": "KR-KTC", "authority": "KR",
                        "status": label, "agency": "무역위원회", "title": r["title"],
                        "product": r["product"], "countries": countries, "targets": targets_of(countries),
                        "stage": stage, "priority": prio, "remedy": remedy,
                        "case_numbers": [r["no"]], "watch": ["국내제소"], "snippets": [],
                        "abstract": f"조사번호 {r['no']} · 진행단계 {r['step']}",
                        "publication_date": d if re.match(r"\d{4}-\d{2}-\d{2}$", d) else None,
                        "html_url": page_url, "pdf_url": None,
                    })
                time.sleep(0.8)
    # 같은 사건이 진행·종결 양쪽에 있으면 종결이 뒤에 처리돼 덮어씀
    res = merge_store(STORE, list({r["id"]: r for r in recs}.values()))
    print(f"[무역위] 신규 {len(res['new_ids'])}건, 누적 {len(res['records'])}건")
    return res


if __name__ == "__main__":
    run()
