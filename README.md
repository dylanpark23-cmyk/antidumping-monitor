# 반덤핑 모니터 — 무역구제 종합 정보 사이트

미국 상무부(ITA)와 국제무역위원회(ITC)가 Federal Register에 올리는 무역구제 공고를 **하루 2회 자동 수집**해서,

- 한국 관련 공고를 찾아 표시하고 (제목·사건번호 `A-580-xxx`·본문까지 확인)
- 단계별로 분류하고 (신규 조사 개시 / 예비판정 / 최종판정 / 연례재심 / 일몰재심 / 우회 등)
- 웹 대시보드로 보여주고
- 새 공고가 생기면 이메일로 알려줍니다.

정식 게재 **전날** 공개되는 "게재예정(Public Inspection)" 공고도 잡기 때문에 하루 먼저 알 수 있어요.
비용은 0원입니다 (GitHub 무료 계정으로 충분).

---

## 설치 방법 (약 15분, 처음 한 번만)

### 1. GitHub 계정 만들기
https://github.com 에서 가입하세요. 이미 있으면 건너뛰세요.

### 2. 저장소(Repository) 만들기
1. 오른쪽 위 **+** → **New repository**
2. Repository name: `antidumping-monitor` (원하는 이름 가능)
3. **Public** 선택 (무료로 웹사이트를 열려면 Public이어야 해요. 수집하는 정보는 모두 미국 정부 공개 자료예요)
4. **Create repository**

### 3. 파일 올리기
1. 받은 zip 파일 압축을 풀어요.
2. 저장소 화면에서 **uploading an existing file** 링크(또는 **Add file → Upload files**)를 눌러요.
3. 압축 푼 폴더 **안의** 파일과 폴더(`collectors`, `web`, `notify`, `data`, `docs`, `tests`, `config.json`, `run_all.py`, `README.md`)를 전부 끌어다 놓고 **Commit changes**.

> ⚠️ `.github` 폴더는 맥/윈도우에서 숨김 폴더라 끌어다 놓기가 잘 안 돼요. 아래 4번처럼 직접 만들어 주세요.

### 4. 자동 실행 파일 만들기
1. 저장소에서 **Add file → Create new file**
2. 파일 이름 칸에 정확히 `.github/workflows/daily.yml` 입력 (슬래시를 치면 폴더가 자동으로 만들어져요)
3. 압축 푼 폴더의 `.github/workflows/daily.yml` 내용을 메모장으로 열어 전체 복사 → 붙여넣기
   (숨김 폴더 보기: 맥은 Finder에서 `Cmd + Shift + .`, 윈도우는 탐색기 **보기 → 숨긴 항목** 체크)
4. **Commit changes**

### 5. 첫 실행
1. 저장소 위쪽 **Actions** 탭 → 왼쪽 **반덤핑 모니터 자동 갱신** → **Run workflow** → **Run workflow**
2. 2~5분 기다리면 초록색 체크가 떠요. 첫 실행에서는 최근 120일치를 한꺼번에 모아요.

### 6. 웹사이트 켜기
1. **Settings → Pages**
2. Source: **Deploy from a branch** / Branch: **main**, 폴더 **/docs** → **Save**
3. 1~2분 뒤 `https://내아이디.github.io/antidumping-monitor/` 에서 대시보드를 볼 수 있어요.

### 7. 이메일 알림 켜기 (선택)
Gmail 계정에 **2단계 인증**이 켜져 있어야 해요.
1. https://myaccount.google.com/apppasswords 에서 앱 비밀번호 생성 (16자리)
2. 저장소 **Settings → Secrets and variables → Actions → New repository secret** 에서 3개 등록:

| 이름 | 값 |
|---|---|
| `MAIL_USER` | 보내는 Gmail 주소 |
| `MAIL_PASS` | 위에서 만든 16자리 앱 비밀번호 (띄어쓰기 없이) |
| `MAIL_TO` | 받을 주소 (여러 명이면 `a@x.com,b@y.com`) |

등록하면 다음 실행부터 **새로 나온 한국 관련 공고**만 메일로 와요. 첫 실행 때 모은 과거 공고는 보내지 않아요.

---

## 매일 어떻게 돌아가나요?

| 한국시간 | 하는 일 |
|---|---|
| 오전 7:17 | 미국 전날 오후에 올라온 **게재예정** 공고 확인 |
| 오후 9:47 | 미국 아침 **정식 게재** 공고 확인 |

GitHub 서버가 붐비면 몇 분에서 수십 분 늦어질 수 있어요. 급할 때는 Actions 탭에서 **Run workflow**로 바로 돌리면 돼요.

## 감시 대상 바꾸기
저장소에서 `config.json`을 열고 연필 아이콘(편집)을 눌러 고친 뒤 Commit하면 돼요.

```json
"watch_countries": ["Korea"],           ← 국가명 (제목·본문에서 찾음)
"watch_country_codes": ["580"],         ← 상무부 사건번호 국가코드 (한국=580)
"watch_companies": ["POSCO", "SeAH"],   ← 회사명을 넣으면 본문에서 이름이 나오는 공고도 잡아요
"email_only_watched": true              ← false로 바꾸면 모든 무역구제 공고를 메일로 받음
```

## 수집 소스 (하루 2회 자동)

| 소스 | 방식 | 들어가는 메뉴 |
|---|---|---|
| KITA 수입규제DB (한국무역협회) | kita.net 대한국 수입규제 DB (44개국, 사건 단위) | 중국·미국·제3국**피제소** (유일 출처) |
| 한국 무역위원회 | ktc.go.kr 조사 진행·종결 목록 | 중국·미국·제3국**제소** (유일 출처) |
| 관세청 수출입통계 | 공공데이터포털 API (키 필요) | DATA |
| UN Comtrade | 공개 미리보기 API | DATA |

> ⚠️ **무역위원회 사이트는 해외 서버 접속을 막고 있어** GitHub에서는 자동 수집이 안 돼요. 새 사건이 생기면 Claude에게 "무역위원회 갱신해줘"라고 하면 국내 브라우저로 업데이트해요. KITA 수입규제DB는 GitHub에서 하루 2회 자동 갱신돼요.

### 관세청 API 키 등록 (DATA 탭 KITA 통계용)
1. https://www.data.go.kr 로그인 → "관세청_품목별 국가별 수출입실적(GW)" 검색 → **활용신청** (자동 승인)
2. 마이페이지 → 인증키 발급현황에서 **일반 인증키(Decoding)** 복사
3. 저장소 Settings → Secrets and variables → Actions → New repository secret → 이름 `CUSTOMS_KEY`, 값 붙여넣기

### DATA 탭 품목 바꾸기
`config.json`의 `watch_hs`에 품목을 추가하세요. `countries`는 조사국 코드(US, CN, IN, EU, JP, VN, TR, BR, AU, CA 등)예요.

## 홈페이지 메뉴 기준 (한국 기준)
| 메뉴 | 뜻 | 소스 |
|---|---|---|
| 중국제소 / 미국제소 / 제3국제소 | 한국(무역위원회·한국 기업)이 그 나라 제품을 **제소**한 건 | 한국 무역위원회 |
| 중국피제소 | 중국 정부가 한국 제품을 조사 | KITA 수입규제DB |
| 미국피제소 | 미국 정부가 한국 제품을 조사 | KITA 수입규제DB |
| 제3국피제소 | EU·인도·튀르키예·브라질 등이 한국 제품을 조사 | KITA 수입규제DB |
| DATA | 관세청(KITA 동일 원자료) 수출 추이, UN Comtrade 조사국 수입 구성 | 관세청, UN Comtrade |

모든 목록은 최신순(최근갱신일)으로 보여요.

메뉴 이름·설명은 `web/build_site.py`의 `SECTIONS` 부분에서 바꿀 수 있어요.

## 대시보드 사용법
- **감시 대상만**: 한국(또는 설정한 회사) 관련만 보기 — 주황 테두리
- **신규 조사만**: 상무부·ITC 신규 조사 개시만 보기
- **본문 중 감시 대상 언급**: 여러 나라 사건이 묶인 연례재심 개시 공고에서 한국 부분만 발췌해서 보여줘요
- 필터 설정은 브라우저에 기억돼요.

## 문제가 생겼을 때
- **Actions가 빨간 X**: 클릭해서 로그를 복사해 Claude에게 보여주세요.
- **"Permission denied" 또는 push 실패**: Settings → Actions → General → Workflow permissions → **Read and write permissions** 선택 → Save
- **메일이 안 옴**: Secrets 이름 철자, 앱 비밀번호(일반 비밀번호 아님)를 확인하세요. 새 한국 공고가 없는 날엔 메일이 안 와요.

## 폴더 구조 (다음 단계 확장용)
```
collectors/   소스별 수집기  (us_federal_register.py → 다음: ktc.py, customs.py, comtrade.py)
data/         수집 결과 JSON (자동 누적)
web/          대시보드 생성기
docs/         공개되는 웹사이트 (자동 생성)
notify/       이메일 알림
tests/        인터넷 없이 돌리는 점검 테스트 (python tests/mock_run.py)
```

출처: [FederalRegister.gov API](https://www.federalregister.gov/developers/documentation/api/v1) — 미국 정부의 공개 API로 키·가입이 필요 없어요.
