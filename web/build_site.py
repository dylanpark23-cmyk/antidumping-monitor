"""data/*.json → docs/index.html (GitHub Pages로 공개되는 홈페이지).

메뉴 기준
  X제소   = X 당국이 조사하는 사건 (예: 미국제소 = 미국 상무부·ITC 조사)
  X피제소 = X산 제품이 조사받는 사건 (예: 중국피제소 = 어느 나라든 중국산 대상 조사)
메뉴 이름·설명은 아래 SECTIONS(자바스크립트)에서 바꿀 수 있어요.
"""
import datetime as dt
import json

from collectors.common import ROOT, load_store

TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AD Monitor 무역구제</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<style>
/* VOICE: 국제통상 컨설팅 회사 홈페이지 — 단정하고 신뢰감 있게
   IDEA: THE ITC 사이트의 주황 띠·좌측 메뉴 구조 + 날짜 눈금자에 공고가 바늘처럼 꽂히는 계기판
   PICTURE: 메인 주황 패널 위 60일 눈금자 (한국 관련 공고 = 흰 바늘)
   COLOUR and TYPE: 흰 바탕, 주황 #f26b1d, 짙은 회색 글자 / 로고 Cinzel, 본문 Noto Sans KR
   LAYOUT: 상단 유틸+로고+7메뉴 → 주황 띠 → 메인(눈금자 패널 | NOTICE) → 6개 분야 타일 → 주황 수치 띠 → 공고 목록 */
:root{color-scheme:light dark;--bg:light-dark(#fff,#16171a);--soft:light-dark(#f4f4f4,#1f2024);--ink:light-dark(#222,#ececec);--mute:light-dark(#6b6b6b,#a3a3a3);--line:light-dark(#dedede,#34363b);--or:#f26b1d;--or2:#e05a0c;--orl:light-dark(#fff3ea,#2a1d14)}
:root[data-theme=light]{color-scheme:light}:root[data-theme=dark]{color-scheme:dark}
*{box-sizing:border-box;min-width:0}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 "Noto Sans KR",system-ui,sans-serif;overflow-x:clip;word-break:keep-all;overflow-wrap:anywhere}
a{color:inherit}
.wrap{max-width:1240px;margin:0 auto;padding:0 max(3vw,16px)}
.fig{position:relative;min-height:170px}.fig>svg{position:absolute;inset:0;width:100%;height:100%}
.scroll{overflow-x:auto}
/* header */
.util{display:flex;justify-content:flex-end;gap:18px;font-size:13px;color:var(--mute);padding-top:10px}
.util a{text-decoration:none}.util a:hover{color:var(--or)}
.hd{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;padding:6px 0 14px;flex-wrap:wrap}
.logo{text-decoration:none;display:block;line-height:1}
.logo b{font:600 clamp(30px,3.6vw,42px)/1 Cinzel,serif;color:var(--or);letter-spacing:.02em;display:block}
.logo small{display:block;font-size:13px;color:var(--mute);margin-top:6px;letter-spacing:.02em}
nav.gnb{display:flex;gap:4px;flex-wrap:wrap}
nav.gnb a{flex:none;font-size:16px;font-weight:700;text-decoration:none;padding:10px 12px;min-height:44px;display:flex;align-items:center;border-bottom:3px solid transparent;white-space:nowrap}
nav.gnb a:hover{color:var(--or)}
nav.gnb a.on{color:var(--or);border-bottom-color:var(--or)}
nav.gnb a.data{margin-left:8px;border-left:1px solid var(--line);padding-left:18px}
.band{height:14px;background:linear-gradient(90deg,var(--or2),var(--or) 60%,#ff8a3d)}
:focus-visible{outline:2px solid var(--or);outline-offset:2px}
/* home */
.hero{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:0;margin-top:24px;border:1px solid var(--line)}
.hp{background:linear-gradient(135deg,#e05a0c,#f26b1d 55%,#ff9152);color:#fff;padding:clamp(22px,3vw,40px);display:flex;flex-direction:column}.hp .fig{flex:1;min-height:190px}
.hp .eyebrow{font-size:15px;opacity:.9;margin:0}
.hp h1{font-size:clamp(28px,3.6vw,44px);line-height:1.15;margin:6px 0 8px;font-weight:700;text-wrap:balance}
.hp p.s{margin:0 0 10px;opacity:.92;font-size:15px}
.notice{background:var(--bg);padding:22px 22px 16px}
.nt{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid var(--ink);padding-bottom:8px;margin-bottom:6px}
.nt b{font-size:18px}.nt a{font-size:13px;color:var(--mute);text-decoration:none}.nt a:hover{color:var(--or)}
.notice ul{list-style:none;margin:0;padding:0}
.notice li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;padding:8px 0;border-bottom:1px dashed var(--line);font-size:14px}
.notice li a{text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.notice li a:hover{color:var(--or)}
.notice time{color:var(--mute);font-size:13px;white-space:nowrap}
.notice .em{color:var(--mute);font-size:14px;padding:12px 0}
.tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-left:1px solid var(--line);border-top:1px solid var(--line);margin-top:28px}
.tile{display:block;text-decoration:none;padding:18px 20px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);min-height:120px}
.tile:hover{background:var(--orl)}
.tile h3{margin:0;font-size:18px}.tile h3 span{color:var(--or)}
.tile .n{font-size:30px;font-weight:500;font-variant-numeric:tabular-nums;line-height:1.2;margin-top:6px}
.tile .n small{font-size:13px;color:var(--mute);font-weight:400;margin-left:6px}
.tile p{margin:2px 0 0;font-size:13px;color:var(--mute)}
.st{display:inline-block;font-size:12px;padding:0 8px;border-radius:99px;margin-left:8px;vertical-align:2px;font-weight:500}
.st.live{background:var(--or);color:#fff}.st.soon{border:1px solid var(--line);color:var(--mute)}
.kband{background:var(--or);color:#fff;margin-top:28px}
.kband .wrap{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))}
.k{padding:20px 12px 20px 0}.k b{display:block;font-size:clamp(26px,3vw,36px);font-weight:500;font-variant-numeric:tabular-nums;line-height:1.2}.k span{font-size:14px;opacity:.92}
h2.sec{font-size:24px;margin:36px 0 4px}
/* sub page (THE ITC style) */
.subvis{height:110px;background:linear-gradient(90deg,#e05a0c,#f26b1d 50%,#ff9152);margin-top:0;display:flex;align-items:center}
.subvis .wrap{width:100%;color:#fff;font-size:clamp(22px,3vw,30px);font-weight:700}
.sub{display:grid;grid-template-columns:240px minmax(0,1fr);gap:40px;margin-top:0}
.lnb{border-right:1px solid var(--line);padding-bottom:40px}
.lnb .ttl{background:var(--or);color:#fff;font-size:22px;font-weight:700;padding:22px 20px;margin-top:28px}
.lnb ul{list-style:none;margin:16px 20px 0 0;padding:0}
.lnb li a{display:flex;align-items:center;min-height:44px;padding:0 6px;border-bottom:1px dashed var(--line);text-decoration:none;font-size:15px;font-weight:500}
.lnb li a.on{border-bottom:2px solid var(--or);font-weight:700}.lnb li a.on::before{content:"";width:12px;height:2px;background:var(--ink);margin-right:8px}
.lnb li a:hover{color:var(--or)}
.lnb .cnt{margin-left:auto;padding-left:6px;color:var(--mute);font-size:13px;font-weight:400}
.ct h2{font-size:clamp(24px,3vw,32px);margin:28px 0 12px}
.crumb{border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:10px 14px;font-size:14px;color:var(--mute)}
.crumb b{color:var(--ink);font-weight:500}
.lead{font-size:16px;margin:22px 0 4px;font-weight:700}.lead+p{margin:0;color:var(--mute);font-size:15px}
/* list */
.ctrl{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0 12px;align-items:center}
input[type=search],select{font:inherit;font-size:16px;min-height:44px;padding:8px 12px;border:1px solid var(--line);border-radius:4px;background:var(--bg);color:var(--ink)}
input[type=search]{flex:1 1 240px}
label.tg{display:flex;gap:8px;align-items:center;min-height:44px;cursor:pointer;font-size:15px}
input[type=checkbox]{width:20px;height:20px;accent-color:var(--or)}
.cline{margin:0 0 8px;font-size:14px;color:var(--mute)}.cline b{color:var(--or);font-size:16px;margin-left:4px}
.list{border-top:2px solid var(--ink);transition:opacity .12s}
.it{padding:14px 4px;border-bottom:1px solid var(--line)}
.it.w{border-left:4px solid var(--or);padding-left:14px;background:var(--orl)}
.meta{display:flex;flex-wrap:wrap;gap:6px 10px;font-size:13px;color:var(--mute);align-items:center}
.tag{display:inline-block;font-size:12px;padding:1px 8px;border:1px solid var(--line);color:var(--ink);white-space:nowrap;border-radius:2px}
.tag.p1{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.tag.w{background:var(--or);color:#fff;border-color:var(--or)}
.tag.pi{border-style:dashed}
.it h3{font-size:16px;font-weight:500;margin:6px 0 2px;line-height:1.45}
.it h3 a{text-decoration:none}.it h3 a:hover{color:var(--or);text-decoration:underline}
.it p{margin:2px 0;font-size:14px;color:var(--mute)}
details{font-size:14px}summary{cursor:pointer;min-height:32px;display:list-item}
details li,details p{color:var(--mute)}
.links a{font-size:13px;margin-right:12px;color:var(--mute)}
.empty{padding:28px 20px;background:var(--soft);margin-top:16px}
.empty h3{margin:0 0 6px;font-size:17px}.empty p{margin:4px 0;color:var(--mute);font-size:15px}
.empty ul{margin:8px 0 0;padding-left:20px;font-size:15px}
.more{display:block;width:100%;min-height:44px;margin-top:12px;font:inherit;background:var(--bg);border:1px solid var(--line);cursor:pointer;color:var(--ink)}
.dgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:20px}
.dcard{border:1px solid var(--line);border-top:3px solid var(--or);padding:18px 20px}
.dcard h3{margin:0 0 6px;font-size:18px}.dcard p{margin:4px 0;font-size:15px;color:var(--mute)}.dcard ul{margin:8px 0 0;padding-left:18px;font-size:15px}
footer{margin-top:56px;background:var(--soft);border-top:1px solid var(--line);padding:22px 0;font-size:13px;color:var(--mute)}
@media(max-width:960px){.hero{grid-template-columns:minmax(0,1fr)}.sub{grid-template-columns:minmax(0,1fr);gap:0}.lnb{border-right:0;padding-bottom:0}.lnb .ttl{margin-top:0}.lnb ul{display:flex;overflow-x:auto;margin:0;gap:4px}.lnb li a{white-space:nowrap;border-bottom:0;padding:0 12px}.lnb li a.on::before{display:none}}
@media(max-width:600px){.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}.kband .wrap,.dgrid{grid-template-columns:repeat(2,minmax(0,1fr))}.dgrid{grid-template-columns:minmax(0,1fr)}nav.gnb{flex-wrap:nowrap;overflow-x:auto;width:100%}nav.gnb a{font-size:15px;padding:10px 9px}nav.gnb a.data{margin-left:0;padding-left:12px}.fig{min-height:130px}.tile{min-height:0;padding:14px}.tile .n{font-size:24px}}
@media(prefers-reduced-motion:no-preference){.tile,.notice li a{transition:background .15s,color .15s}}
</style></head><body>
<header class="wrap">
<div class="util"><a href="#home">HOME</a><a href="#src">데이터 출처</a><span id="upd"></span></div>
<div class="hd"><a class="logo" href="#home"><b>AD MONITOR</b><small>Trade Remedy Monitor · 무역구제 종합정보</small></a>
<nav class="gnb scroll" id="gnb" aria-label="주 메뉴"></nav></div>
</header>
<div class="band"></div>
<main id="app"></main>
<footer><div class="wrap">출처: FederalRegister.gov (미국 상무부·ITC) — 하루 2회 자동 갱신. "게재예정"은 정식 게재 전날 공개된 공고입니다. 본 사이트 정보는 참고용이며 원문을 확인하세요.</div></footer>
<script id="data" type="application/json">__DATA__</script>
<script>
{
const D=JSON.parse(document.getElementById('data').textContent);
const R=D.records, TODAY=new Date(D.built+'T00:00:00Z');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const $=id=>document.getElementById(id);
const days=d=>d?Math.round((TODAY-new Date(d+'T00:00:00Z'))/864e5):9999;
const isW=r=>!!(r.watch&&r.watch.length);
const cc=c=>/korea/i.test(c)?'KR':(/taiwan/i.test(c)?'OT':(/china/i.test(c)?'CN':(/united states/i.test(c)?'US':'OT')));
R.forEach(r=>{r.auth=r.authority||'US';r.tg=[...new Set((r.countries||[]).map(cc))]});

/* 메뉴 정의 — 이름·설명·데이터 출처를 여기서 바꾸면 됩니다 */
const SECTIONS=[
 {id:'cn-file',name:'중국제소',full:'중국 제소',desc:'중국 상무부(MOFCOM)가 조사하는 무역구제 사건',test:r=>r.auth==='CN',krDefault:true,live:false,
  plan:['중국 상무부 무역구제조사국 공고 (개시·예비·최종·재심)','한국산 대상 사건 우선 표시']},
 {id:'cn-resp',name:'중국피제소',full:'중국 피제소',desc:'세계 각국이 중국산 제품을 조사하는 사건',test:r=>r.tg.includes('CN'),krDefault:false,live:true,
  plan:['현재: 미국 상무부·ITC의 중국산 조사 자동 분류','예정: 무역위원회(한국)·EU·인도 등의 중국산 조사']},
 {id:'us-file',name:'미국제소',full:'미국 제소',desc:'미국 상무부(ITA)·국제무역위원회(ITC)가 조사하는 사건',test:r=>r.auth==='US',krDefault:true,live:true,plan:[]},
 {id:'us-resp',name:'미국피제소',full:'미국 피제소',desc:'세계 각국이 미국산 제품을 조사하는 사건',test:r=>r.tg.includes('US'),krDefault:false,live:false,
  plan:['무역위원회(한국)의 미국산 조사','중국·EU·인도 등의 미국산 조사']},
 {id:'third-file',name:'제3국제소',full:'제3국 제소',desc:'미국·중국 외 국가(EU, 인도, 호주, 캐나다 등)가 조사하는 사건',test:r=>!['US','CN','KR'].includes(r.auth),krDefault:true,live:false,
  plan:['EU 집행위원회 (Official Journal)','인도 DGTR','호주 ADC · 캐나다 CBSA · 브라질 · 튀르키예 등']},
 {id:'third-resp',name:'제3국피제소',full:'제3국 피제소',desc:'미국·중국·한국 외 국가 제품이 조사받는 사건',test:r=>r.tg.includes('OT'),krDefault:false,live:true,
  plan:['현재: 미국 상무부·ITC의 제3국산 조사 자동 분류','예정: 무역위원회(한국)·EU 등의 제3국산 조사']},
];
const GROUPS=[['all','전체'],['new','신규 조사'],['det','예비·최종판정'],['rev','재심'],['etc','기타']];
const grp=r=>r.priority===1?'new':(/판정|명령/.test(r.stage)?'det':(/재심/.test(r.stage)?'rev':'etc'));

$('upd').textContent='업데이트 '+D.built_at;
$('gnb').innerHTML=SECTIONS.map(s=>`<a href="#${s.id}" data-r="${s.id}">${esc(s.name)}</a>`).join('')+`<a class="data" href="#data" data-r="data">DATA</a>`;

const st={q:'',period:60,kr:null};
function card(r){
  return `<article class="it${isW(r)?' w':''}"><div class="meta"><span>${esc(r.publication_date)}</span><span>${esc(r.agency)}</span>
  <span class="tag${r.priority===1?' p1':''}">${esc(r.stage)}</span><span class="tag">${esc(r.remedy)}</span>
  ${r.status==='게재예정'?'<span class="tag pi">게재예정</span>':''}${(r.watch||[]).map(w=>`<span class="tag w">${esc(w)}</span>`).join('')}</div>
  <h3><a href="${esc(r.html_url)}">${esc(r.title)}</a></h3>
  ${r.case_numbers&&r.case_numbers.length?`<p>사건번호 ${esc(r.case_numbers.slice(0,8).join(', '))}${r.case_numbers.length>8?' 외':''}</p>`:''}
  ${r.snippets&&r.snippets.length?`<details><summary>본문 중 한국 관련 언급 ${r.snippets.length}곳</summary><ul>${r.snippets.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details>`:''}
  ${r.abstract?`<details><summary>요약(원문)</summary><p>${esc(r.abstract)}</p></details>`:''}
  <div class="links">${r.html_url?`<a href="${esc(r.html_url)}">원문</a>`:''}${r.pdf_url?`<a href="${esc(r.pdf_url)}">PDF</a>`:''}</div></article>`;
}
function controls(krOn){
  return `<div class="ctrl"><input type="search" id="q" value="${esc(st.q)}" placeholder="품목·국가·사건번호 검색 (예: nails, A-580)" aria-label="검색">
  <select id="period" aria-label="기간">${[[14,'최근 2주'],[60,'최근 60일'],[365,'최근 1년'],[99999,'전체']].map(([v,l])=>`<option value="${v}"${st.period==v?' selected':''}>${l}</option>`).join('')}</select>
  <label class="tg"><input type="checkbox" id="kr"${krOn?' checked':''}> 한국 관련만</label></div><p class="cline" id="cline" aria-live="polite"></p><div class="list" id="list"></div>`;
}
let shown=50,rowsNow=[];
function fill(base,krOn){
  const q=st.q.trim().toLowerCase();
  rowsNow=base.filter(r=>days(r.publication_date)<=st.period&&(!krOn||isW(r))&&(!q||[r.title,r.product,(r.countries||[]).join(' '),(r.case_numbers||[]).join(' '),r.abstract,(r.snippets||[]).join(' ')].join(' ').toLowerCase().includes(q)));
  const pl={14:'최근 2주',60:'최근 60일',365:'최근 1년',99999:'전체 기간'}[st.period]||'';
  const c=$('cline');if(c)c.innerHTML=`${esc(pl)} · ${krOn?'한국 관련':'모든 국가'}${q?` · "${esc(st.q)}"`:''} <b>${rowsNow.length}건</b>`;
  const L=$('list');if(L){L.style.opacity=.35;setTimeout(()=>L.style.opacity=1,120)}
  shown=50;paint();
}
function paint(){
  const L=$('list');if(!L)return;
  L.innerHTML=rowsNow.length?rowsNow.slice(0,shown).map(card).join('')+(rowsNow.length>shown?`<button class="more" id="more">더보기 (${rowsNow.length-shown}건 남음)</button>`:''):
   '<div class="empty"><p>조건에 맞는 공고가 없어요. "한국 관련만"을 끄거나 기간을 넓혀보세요.</p></div>';
  const m=$('more');if(m)m.addEventListener('click',()=>{shown+=50;paint()});
}
function wire(base,krDefault){
  let kr=st.kr??krDefault;
  const go=()=>fill(base,kr);
  $('q').addEventListener('input',e=>{st.q=e.target.value;go()});
  $('period').addEventListener('change',e=>{st.period=+e.target.value;go()});
  $('kr').addEventListener('change',e=>{kr=e.target.checked;st.kr=kr;go()});
  go();
}
const recent=(base,n)=>base.filter(r=>days(r.publication_date)<=n);

function home(){
  const w14=recent(R.filter(isW),14), n1=w14.filter(r=>r.priority===1).length, pi=R.filter(r=>r.status==='게재예정').length;
  const notice=R.filter(isW).slice(0,6);
  $('app').innerHTML=`<div class="wrap">
  <section class="hero"><div class="hp"><p class="eyebrow">글로벌 무역구제 모니터</p>
   <h1>${n1?`최근 2주, 한국 관련 신규 조사 ${n1}건`:`최근 2주 한국 관련 공고 ${w14.length}건`}</h1>
   <p class="s">흰 바늘이 한국 관련 공고, 점은 신규 조사 개시예요. 최근 60일.</p>
   <div class="fig"><svg id="scale" role="img" aria-label="최근 60일 공고 눈금자"></svg></div></div>
   <aside class="notice"><div class="nt"><b>NOTICE</b><a href="#us-file">더보기 +</a></div>
   ${notice.length?`<ul>${notice.map(r=>`<li><a href="${esc(r.html_url)}" title="${esc(r.title)}">${esc(r.product||r.title)} · ${esc(r.stage)}</a><time>${esc(r.publication_date)}</time></li>`).join('')}</ul>`:'<p class="em">아직 한국 관련 공고가 없어요.</p>'}
   </aside></section>
  <div class="tiles">${SECTIONS.map(s=>{const n=recent(R.filter(s.test),60).length;return `<a class="tile" href="#${s.id}"><h3>${esc(s.name.replace(/(제소|피제소)$/,''))}<span>${esc(s.name.match(/(피제소|제소)$/)[0])}</span><em class="st ${s.live?'live':'soon'}">${s.live?'연결됨':'준비 중'}</em></h3>
    <div class="n">${s.live?n:'–'}<small>${s.live?'최근 60일':''}</small></div><p>${esc(s.desc)}</p></a>`}).join('')}</div></div>
  <section class="kband"><div class="wrap">${[['최근 2주 한국 관련',w14.length],['그중 신규 조사',n1],['게재예정',pi],['누적 수집',R.length]].map(([l,v])=>`<div class="k"><b>${v}</b><span>${l}</span></div>`).join('')}</div></section>
  <div class="wrap"><h2 class="sec">최근 공고</h2>${controls(st.kr??true)}</div>`;
  wire(R,true);
  const s=$('scale');
  const draw=()=>{
    const W=s.clientWidth,H=s.clientHeight,pad=6,span=60,base=H-30,x=d=>pad+(W-2*pad)*(1-d/span);
    let g=`<line x1="${pad}" y1="${base}" x2="${W-pad}" y2="${base}" stroke="#fff" stroke-width="1.5"/>`;
    for(let d=0;d<=span;d++){const big=d%7===0;g+=`<line x1="${x(d)}" y1="${base}" x2="${x(d)}" y2="${base+(big?9:4)}" stroke="#fff" stroke-opacity="${big?.9:.45}"/>`;
      if(big&&(W>520||d%14===0)){const t=new Date(TODAY-d*864e5);g+=`<text x="${x(d)}" y="${base+24}" font-size="12" text-anchor="${d===0?'end':'middle'}" fill="#fff" fill-opacity=".85">${d===0?'오늘':(t.getUTCMonth()+1)+'/'+t.getUTCDate()}</text>`}}
    const stack={};
    R.filter(r=>days(r.publication_date)<=span).forEach(r=>{const d=Math.max(0,days(r.publication_date));stack[d]=(stack[d]||0)+1;const h=Math.min(base-8,(w0=>w0?46:26)(isW(r))+stack[d]*12),w=isW(r);
      g+=`<line x1="${x(d)}" y1="${base}" x2="${x(d)}" y2="${base-h}" stroke="#fff" stroke-opacity="${w?1:.35}" stroke-width="${w?2.5:1.5}"/>`;
      if(w&&r.priority===1)g+=`<circle cx="${x(d)}" cy="${base-h}" r="4.5" fill="#fff"/>`});
    s.innerHTML=g;
  };
  window.__ro&&window.__ro.disconnect();window.__ro=new ResizeObserver(draw);window.__ro.observe(s);
}

function shell(title,lnbTitle,items,crumb,body){
  return `<div class="subvis"><div class="wrap">${esc(title)}</div></div><div class="wrap sub">
  <aside class="lnb"><div class="ttl">${esc(lnbTitle)}</div><ul>${items}</ul></aside>
  <div class="ct"><h2>${esc(crumb[crumb.length-1])}</h2><div class="crumb">Home &gt; ${crumb.slice(0,-1).map(esc).join(' &gt; ')} &gt; <b>${esc(crumb[crumb.length-1])}</b></div>${body}</div></div>`;
}
function section(sec,g){
  const all=R.filter(sec.test), gn=GROUPS.find(x=>x[0]===g)||GROUPS[0];
  const items=GROUPS.map(([k,l])=>`<li><a href="#${sec.id}${k==='all'?'':'-'+k}" class="${k===gn[0]?'on':''}">${l}<span class="cnt">${all.filter(r=>k==='all'||grp(r)===k).length}</span></a></li>`).join('');
  const base=all.filter(r=>gn[0]==='all'||grp(r)===gn[0]);
  const body=sec.live||all.length?`<p class="lead">${esc(sec.desc)}</p><p>${sec.plan.length?esc(sec.plan.join(' · ')):'상무부·ITC 공고를 하루 2회 자동 수집합니다.'}</p>${controls(st.kr??sec.krDefault)}`:
   `<p class="lead">${esc(sec.desc)}</p><div class="empty"><h3>데이터 연결 준비 중</h3><p>다음 단계에서 아래 출처를 연결할 예정이에요.</p><ul>${sec.plan.map(p=>`<li>${esc(p)}</li>`).join('')}</ul></div>`;
  $('app').innerHTML=shell(sec.full,sec.name,items,[sec.name,gn[1]],body);
  if($('list'))wire(base,sec.krDefault);
}
function data(sub){
  const subs=[['kita','KITA 한국 수출입'],['comtrade','UN Comtrade 세계 교역']];
  const cur=subs.find(x=>x[0]===sub)||subs[0];
  const items=subs.map(([k,l])=>`<li><a href="#data-${k}" class="${k===cur[0]?'on':''}">${l}</a></li>`).join('');
  const C={kita:[['품목별 한국 수출입 추이','사건 품목(HS코드)의 국가별 월간 수출입 금액·중량. 관세청 수출입무역통계 API로 연결 예정 (KITA 통계와 같은 통관 원자료).',['사건 HS코드 자동 연결','조사대상기간(POI) 전후 비교','단가(금액÷중량) 추이']],
              ['사건 연동','사건 화면에서 "통계 보기"를 누르면 해당 품목 통계로 이동',['반덤핑 부과 전후 수입 변화','제3국 우회 의심 신호']]],
           comtrade:[['세계 교역 구조','UN Comtrade로 각국의 품목별 수입 상대국 비중을 보여줄 예정',['조사국의 수입 상위 국가','한국 점유율 변화']],
              ['유의 사항','월별 자료는 약 6개월, 연간 자료는 약 18개월 늦게 공개돼요. 최근 동향은 KITA(관세청) 자료를 보세요.',['무료 키: 하루 500회 호출']]]};
  const body=`<p class="lead">무역구제 판단에 필요한 교역 통계</p><p>2단계(관세청)·4단계(UN Comtrade)에서 연결할 예정이에요.</p>
   <div class="dgrid">${C[cur[0]].map(([h,p,l])=>`<div class="dcard"><h3>${esc(h)}<em class="st soon">준비 중</em></h3><p>${esc(p)}</p><ul>${l.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`).join('')}</div>`;
  $('app').innerHTML=shell('DATA','DATA',items,['DATA',cur[1]],body);
}
function src(){
  const items=`<li><a class="on" href="#src">데이터 출처</a></li>`;
  const rows=[['미국 상무부·ITC','Federal Register API','연결됨'],['중국 상무부','MOFCOM 무역구제조사국','준비 중'],['한국 무역위원회','ktc.go.kr 공고·월간통계','준비 중'],['EU·인도·기타','각국 관보·조사당국','준비 중'],['한국 수출입 통계','관세청 API (KITA 동일 원자료)','준비 중'],['세계 교역 통계','UN Comtrade API','준비 중']];
  $('app').innerHTML=shell('데이터 출처','안내',items,['안내','데이터 출처'],`<div class="scroll"><table style="width:100%;border-collapse:collapse;margin-top:20px;font-size:15px"><thead><tr>${['구분','출처','상태'].map(h=>`<th style="text-align:left;border-bottom:2px solid var(--ink);padding:8px">${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td style="border-bottom:1px solid var(--line);padding:10px 8px;white-space:nowrap">${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
}

function route(){
  const h=(location.hash||'#home').slice(1);
  let key='home';
  if(h.startsWith('data')){key='data';data(h.split('-')[1])}
  else if(h==='src'){key='src';src()}
  else{const sec=SECTIONS.find(s=>h===s.id||h.startsWith(s.id+'-'));
    if(sec){key=sec.id;section(sec,h.slice(sec.id.length+1)||'all')}else home()}
  document.querySelectorAll('#gnb a').forEach(a=>a.classList.toggle('on',a.dataset.r===key));
  if(key!=='home')window.scrollTo(0,0);
}
addEventListener('hashchange',route);route();
}
</script></body></html>
"""


def build() -> None:
    now = dt.datetime.utcnow() + dt.timedelta(hours=9)
    records = load_store("us_fr.json")
    for r in records:
        r.setdefault("authority", "US")
    payload = {
        "built": now.date().isoformat(),
        "built_at": now.strftime("%m/%d %H:%M KST"),
        "records": records,
    }
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", data), encoding="utf-8")
    (ROOT / "docs" / ".nojekyll").write_text("")
    print(f"[사이트] {out} 생성 ({len(records)}건)")


if __name__ == "__main__":
    build()
