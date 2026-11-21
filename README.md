# ⚖️ Legal Article Network (`legal-article-network`)

**다중 법령·판례 조항(Article-to-Article) 연계 지식 그래프 시각화 & AI 법률 리서치 웹 앱**  
*(Powered by Streamlit · NetworkX · Pyvis · Gemini API)*

여러 법령(예: EU CDSM 지침, InfoSoc 지침, E-Commerce/DSA, EU AI Act 및 핵심 판례)의 개별 **조항(Article)** 들이 서로 어떻게 **인용·개정·특별법 우선적용·예외·충돌**하는지 거미줄 형태의 인터랙티브 네트워크 그래프로 시각화하고, 조항 클릭 시 전문·요약·법률 해설을 즉시 제공하는 리걸테크 웹 애플리케이션입니다.

---

## ✨ 주요 기능 (Key Features)

1. **초정밀 조항 단위 매핑 (Article-to-Article Network Graph)**
   - `NetworkX` + `Pyvis` 기반 인터랙티브 지식 그래프 (마우스 드래그, 줌인/줌아웃, 물리 엔진 고정/해제, 화면 맞춤 지원)
   - 연결 중심성(Degree Centrality)에 따라 핵심 허브 조항(예: `CDSM 제17조`)의 크기를 자동 강조
2. **실시간 노드 & 연결선 클릭 상세 분석창 (Interactive Legal Inspector)**
   - 그래프 위 **조항 원(Node)** 클릭 시 우측 패널에 **조항 전문, 핵심 요약, 에이전트 법률 해설, 연결된 타 법령 바로가기 버튼** 즉시 표시
   - **연결선(Edge)** 클릭 시 두 조항 간의 구체적인 **충돌·예외·우선적용 법리 해설** 표시
3. **법적 관계 유형별 색상·선 스타일 및 필터링**
   - `특별법 우선 (Lex Specialis)`, `충돌·적용 배제 (Conflict)`, `예외·한계 설정 (Exception, 점선)`, `개정·보완 (Amended)`, `정의·인용 참조 (Citation, 점선)` 별 필터링
4. **4대 AI 법률 리서치 두뇌 (Legal Research Studio)**
   - **다중 법령 벤 다이어그램 교차 비교**
   - **법적 충돌 및 사각지대(Gap) 자동 탐지**
   - **입법 연혁 및 판례 흐름 타임라인**
   - **파트너 변호사 보고용 2페이지 법률 검토 메모(Memo) 생성 및 `.md` 다운로드**
5. **3가지 유연한 데이터 입력 방식**
   - 내장 EU 저작권·AI·플랫폼법 샘플 즉시 탐색
   - NotebookLM / AI 에이전트가 추출한 JSON 붙여넣기 또는 `.json` 업로드 (앱 내 **프롬프트 자동 생성기** 탑재)
   - PDF / DOCX / TXT / MD 법령 문서 업로드 후 **Gemini API**로 원클릭 자동 추출

---

## 🚀 GitHub & Streamlit Community Cloud 배포 방법

1. **GitHub 새 저장소(Repository) 생성**
   - GitHub 우측 상단 **`New repository`** 클릭 → 이름 입력 (예: `legal-article-network`) → **`Create repository`** 클릭
2. **파일 업로드**
   - 생성된 저장소 화면에서 **`uploading an existing file`** 클릭 후 아래 파일들을 드래그 앤 드롭하고 **`Commit changes`** 클릭:
     - `app.py`
     - `requirements.txt`
     - `sample_legal_graph.json`
     - `README.md`
     - `.gitignore`
3. **Streamlit Community Cloud 연동**
   - [share.streamlit.io](https://share.streamlit.io) 접속 → 우측 상단 **`Create app`** 클릭
   - **Repository:** `MINSUPERRICH/legal-article-network` 선택
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - *(선택)* **Advanced settings → Secrets**에 Gemini API 키를 미리 등록하려면 아래 형식으로 입력:
     ```toml
     GEMINI_API_KEY = "여기에_본인의_GEMINI_API_KEY_입력"
     ```
   - **`Deploy!`** 클릭하면 전 세계 어디서나 접속 가능한 웹 앱 URL이 생성됩니다.
