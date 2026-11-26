"""중국 상무부(MOFCOM) 공고 중 무역구제 건 수집 → data/cn_mofcom.json"""
import datetime as dt
import re

from collectors.common import get_text, merge_store, targets_of

BASE = "https://www.mofcom.gov.cn"
STORE = "cn_mofcom.json"
RELEVANT = re.compile(r"反倾销|反补贴|保障措施|倾销|补贴")
COUNTRY_KO = {"韩国": "한국", "美国": "미국", "日本": "일본", "欧盟": "EU", "印度": "인도", "台湾地区": "대만",
              "中国台湾地区": "대만", "英国": "영국", "加拿大": "캐나다", "澳大利亚": "호주", "泰国": "태국",
              "马来西亚": "말레이시아", "印度尼西亚": "인도네시아", "新加坡": "싱가포르", "俄罗斯": "러시아"}


def parse_list(html_text: str) -> list:
    out = []
    pat = re.compile(r'<a href="([^"]*/art/\d{4}/art_[0-9a-f]{32}\.html)"\s+title="([^"]+)"[^>]*>.*?</a>\s*(\d{4}-\d{2}-\d{2})', re.S)
    for href, title, date in pat.findall(html_text):
        out.append({"href": href if href.startswith("http") else BASE + href, "title": title, "date": date})
    return out


def countries_of(title: str) -> list:
    m = re.search(r"原产于(.+?)的", title)
    if not m:
        return []
    return [c for c in re.split(r"[、和及与,，]", m.group(1)) if c]


def product_of(title: str) -> str:
    m = re.search(r"进口(.+?)(?:发起|所适用|反倾销|反补贴|作出|继续|期终|期中|保障措施|实施|的反|调查|进行)", title)
    return m.group(1) if m else ""


def stage_of(title: str) -> tuple:
    t = title
    if "期终复审" in t and "立案" in t:
        return "일몰재심 개시", 2
    if "期中复审" in t and "立案" in t:
        return "중간재심 개시", 2
    if "立案" in t:
        return "신규 조사 개시(중국)", 1
    if "初裁" in t or "初步裁定" in t:
        return "예비판정", 2
    if "终裁" in t or "最终裁定" in t:
        return "최종판정", 2
    if "期终复审" in t:
        return "일몰재심 결과", 2
    if "期中复审" in t:
        return "중간재심 결과", 2
    if "终止" in t:
        return "조사 종료", 2
    if "延长" in t or "继续" in t:
        return "조사기간 연장·재심", 3
    return "기타", 3


def remedy_of(title: str) -> str:
    if "保障措施" in title:
        return "SG"
    ad, cvd = "反倾销" in title or "倾销" in title, "反补贴" in title or "补贴" in title
    return "AD/CVD" if ad and cvd else ("CVD" if cvd else "AD")


def run() -> dict:
    today = dt.date.today()
    years = [today.year] + ([today.year - 1] if today.month <= 3 else [])
    recs = []
    for y in years:
        for item in parse_list(get_text(f"{BASE}/zcfb/blgg/gg/{y}/index.html")):
            t = item["title"]
            if not RELEVANT.search(t):
                continue
            countries = countries_of(t)
            stage, prio = stage_of(t)
            art = re.search(r"art_([0-9a-f]{32})", item["href"]).group(1)
            recs.append({
                "id": f"MOFCOM-{art}", "source": "CN-MOFCOM", "authority": "CN", "status": "게재",
                "agency": "중국 상무부", "title": t, "product": product_of(t),
                "countries": [COUNTRY_KO.get(c, c) for c in countries], "targets": targets_of(countries),
                "stage": stage, "priority": prio, "remedy": remedy_of(t),
                "case_numbers": re.findall(r"\d{4}年第\d+号", t), "watch": ["Korea"] if "韩国" in t else [],
                "snippets": [], "abstract": "", "publication_date": item["date"],
                "html_url": item["href"], "pdf_url": None,
            })
    res = merge_store(STORE, recs)
    print(f"[중국 상무부] 신규 {len(res['new_ids'])}건, 누적 {len(res['records'])}건")
    return res


if __name__ == "__main__":
    run()
