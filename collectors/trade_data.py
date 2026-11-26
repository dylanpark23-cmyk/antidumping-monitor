"""DATA 탭용 무역통계 수집 → data/trade_data.json

- 관세청 품목별·국가별 수출입실적 API (KITA 통계와 같은 통관 원자료)
    GitHub Secrets 에 CUSTOMS_KEY (공공데이터포털 일반 인증키, Decoding 키) 가 있어야 동작
- UN Comtrade: 키 없이 쓰는 공개 미리보기 API (선택: COMTRADE_KEY 를 넣으면 정식 API 사용)
- 대상 품목은 config.json 의 watch_hs 에서 지정
"""
import datetime as dt
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET

from collectors.common import _get, get_json, load_config, save_store

CUSTOMS = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"
COMTRADE_PREVIEW = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
COMTRADE_FULL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
M49 = {"US": 842, "CN": 156, "IN": 699, "JP": 392, "VN": 704, "TR": 792, "BR": 76, "AU": 36, "CA": 124,
       "EU": 97, "MX": 484, "ID": 360, "TH": 764, "MY": 458, "KR": 410, "GB": 826, "ZA": 710}


def customs_monthly(key: str, hs: str, cty: str, months: int = 24) -> list:
    """최근 months개월 한국↔cty 월별 수출입 (1년 단위로 나눠 조회)"""
    end = dt.date.today().replace(day=1) - dt.timedelta(days=1)
    k = end.year * 12 + end.month - 1 - (months - 1)
    start = dt.date(k // 12, k % 12 + 1, 1)
    rows, cur = [], start
    while cur <= end:
        chunk_end = min(end, dt.date(cur.year + (cur.month + 10) // 12, (cur.month + 10) % 12 + 1, 1))
        q = urllib.parse.urlencode({"serviceKey": key, "strtYymm": cur.strftime("%Y%m"),
                                    "endYymm": chunk_end.strftime("%Y%m"), "hsSgn": hs, "cntyCd": cty})
        root = ET.fromstring(_get(f"{CUSTOMS}?{q}"))
        code = (root.findtext(".//resultCode") or "").strip()
        if code and code not in ("00", "0"):
            raise RuntimeError(f"관세청 API 오류 {code}: {root.findtext('.//resultMsg')}")
        for it in root.iter("item"):
            ym = (it.findtext("year") or "").strip()
            if not re.match(r"\d{4}\.\d{2}$", ym):
                continue   # '총계' 행 제외
            rows.append({"ym": ym.replace(".", "-"),
                         "exp_usd": float(it.findtext("expDlr") or 0), "exp_kg": float(it.findtext("expWgt") or 0),
                         "imp_usd": float(it.findtext("impDlr") or 0), "imp_kg": float(it.findtext("impWgt") or 0)})
        nm = chunk_end.month % 12 + 1
        cur = dt.date(chunk_end.year + (1 if nm == 1 else 0), nm, 1)
        time.sleep(0.3)
    agg = {}
    for r in rows:   # HS 10단위로 조회되면 같은 달 여러 행 → 합산
        a = agg.setdefault(r["ym"], {"ym": r["ym"], "exp_usd": 0, "exp_kg": 0, "imp_usd": 0, "imp_kg": 0})
        for k in ("exp_usd", "exp_kg", "imp_usd", "imp_kg"):
            a[k] += r[k]
    return sorted(agg.values(), key=lambda r: r["ym"])


def comtrade_imports(reporter: str, hs: str) -> dict:
    """reporter 국가의 해당 HS 수입 상대국별 금액 (최근 이용 가능한 연도)"""
    code = M49.get(reporter)
    if not code:
        return {}
    key = os.environ.get("COMTRADE_KEY")
    for year in (dt.date.today().year - 1, dt.date.today().year - 2):
        q = {"reporterCode": code, "period": year, "cmdCode": hs[:6], "flowCode": "M", "includeDesc": "true"}
        if key:
            q["subscription-key"] = key
        data = get_json(f"{COMTRADE_FULL if key else COMTRADE_PREVIEW}?{urllib.parse.urlencode(q)}")
        rows = [r for r in (data.get("data") or []) if r.get("partnerCode") not in (0, None)
                and (r.get("customsCode") in (None, "C00")) and (r.get("motCode") in (None, 0))
                and (r.get("partner2Code") in (None, 0))]
        if rows:
            by = {}
            for r in rows:
                name = r.get("partnerDesc") or str(r.get("partnerCode"))
                by[name] = by.get(name, 0) + float(r.get("primaryValue") or 0)
            total = sum(by.values()) or 1
            top = sorted(by.items(), key=lambda x: -x[1])[:12]
            kor = next((v for k, v in by.items() if "korea" in k.lower()), 0)
            return {"year": year, "total_usd": total, "korea_usd": kor, "korea_share": kor / total,
                    "top": [{"partner": k, "usd": v, "share": v / total} for k, v in top]}
        time.sleep(1.2)
    return {}


def run() -> dict:
    cfg = load_config()
    items = cfg.get("watch_hs", [])
    key = os.environ.get("CUSTOMS_KEY")
    out = {"updated": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
           "customs_enabled": bool(key), "items": []}
    for it in items:
        hs, name, ctys = str(it.get("hs", "")), it.get("name", ""), it.get("countries", [])
        entry = {"hs": hs, "name": name, "customs": {}, "comtrade": {}, "errors": []}
        for c in ctys:
            if key and c != "EU":
                try:
                    entry["customs"][c] = customs_monthly(key, hs, c)
                except Exception as e:
                    entry["errors"].append(f"관세청 {c}: {e}")
            try:
                ct = comtrade_imports(c, hs)
                if ct:
                    entry["comtrade"][c] = ct
            except Exception as e:
                entry["errors"].append(f"Comtrade {c}: {e}")
            time.sleep(1.2)
        out["items"].append(entry)
    save_store("trade_data.json", out)
    print(f"[DATA] 품목 {len(items)}개 갱신 (관세청 {'사용' if key else '키 없음 — 건너뜀'})")
    return out


if __name__ == "__main__":
    run()
