"""신규 공고 이메일 알림 (Gmail 앱 비밀번호 사용).

GitHub 저장소 Settings → Secrets 에 아래 3개가 있을 때만 발송합니다.
  MAIL_USER : 보내는 Gmail 주소
  MAIL_PASS : 그 Gmail의 '앱 비밀번호'(16자리)
  MAIL_TO   : 받는 주소 (여러 명이면 쉼표로 구분)
"""
import html
import os
import smtplib
from email.mime.text import MIMEText


def _row(r: dict) -> str:
    watch = ", ".join(r.get("watch") or [])
    badge = ' style="color:#ff4f00;font-weight:600"' if r.get("priority") == 1 else ""
    snip = ""
    if r.get("snippets"):
        snip = "<br><small style='color:#666'>" + html.escape(r["snippets"][0][:220]) + "</small>"
    return (
        f"<tr><td style='padding:6px;white-space:nowrap'>{html.escape(r.get('publication_date') or '')}</td>"
        f"<td style='padding:6px'{badge}>{html.escape(r['stage'])}</td>"
        f"<td style='padding:6px'>{html.escape(r['agency'])} · {html.escape(r['remedy'])}"
        f"{' · 게재예정' if r['status'] == '게재예정' else ''}</td>"
        f"<td style='padding:6px'><a href='{html.escape(r.get('html_url') or '')}'>{html.escape(r['title'])}</a>"
        f"{'<br><b>' + html.escape(watch) + '</b>' if watch else ''}{snip}</td></tr>"
    )


def send(new_records: list, only_watched: bool = True, site_url: str = "") -> None:
    user, pw, to = (os.environ.get(k) for k in ("MAIL_USER", "MAIL_PASS", "MAIL_TO"))
    if not (user and pw and to):
        print("[메일] 설정이 없어 발송을 건너뜀")
        return
    items = [r for r in new_records if r.get("watch")] if only_watched else list(new_records)
    if not items:
        print("[메일] 보낼 신규 공고 없음")
        return
    items.sort(key=lambda r: (r.get("priority", 3), r.get("publication_date") or ""))
    n1 = sum(1 for r in items if r.get("priority") == 1)
    subject = f"[반덤핑 모니터] 신규 {len(items)}건" + (f" (신규 조사 {n1}건)" if n1 else "")
    body = (
        "<div style='font-family:sans-serif'>"
        f"<p>미국 Federal Register 신규 무역구제 공고 {len(items)}건입니다.</p>"
        "<table border='1' style='border-collapse:collapse;font-size:14px'>"
        "<tr><th>게재일</th><th>단계</th><th>기관</th><th>공고</th></tr>"
        + "".join(_row(r) for r in items)
        + "</table>"
        + (f"<p><a href='{html.escape(site_url)}'>대시보드에서 보기</a></p>" if site_url else "")
        + "</div>"
    )
    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.sendmail(user, [x.strip() for x in to.split(",") if x.strip()], msg.as_string())
    print(f"[메일] {len(items)}건 발송 → {to}")
