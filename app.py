import html
import io
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import networkx as nx
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

# Optional imports for file parsing & Gemini API
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


# =====================================================================
# 1. 기본 설정 및 내장 폴백 데이터 (Built-in Fallback Dataset)
# =====================================================================
st.set_page_config(
    page_title="Legal Article Network | 법률 조항 연계 시각화",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

FALLBACK_GRAPH_DATA: Dict[str, Any] = {
    "nodes": [
        {
            "id": "CDSM_17",
            "label": "CDSM 제17조",
            "title": "온라인 콘텐츠 공유 서비스 제공자(OCSSP) 책임",
            "group": "CDSM",
            "year": 2019,
            "summary": "OCSSP가 이용자 업로드 저작물에 대해 직접 공중전달 행위를 수행하는 것으로 규정하고, 라이선스 체결 또는 최선의 노력(Best Efforts) 입증 시에만 면책합니다.",
            "full_text": "Article 17(1): OCSSP는 이용자가 업로드한 보호 저작물에 공중이 접근하도록 할 때 공중전달 행위를 수행한다. Article 17(4): 허락이 없는 경우 허락 확보·사전 차단·통지 후 삭제 및 재업로드 방지에 관한 최선의 노력을 입증해야 한다.",
            "commentary": "InfoSoc 제3조에 대한 특별법(Lex Specialis)으로 작동하며 E-Commerce 제14조 호스팅 면책을 배제합니다.",
        },
        {
            "id": "InfoSoc_3",
            "label": "InfoSoc 제3조",
            "title": "공중전달권 및 공중이용제공권",
            "group": "InfoSoc",
            "year": 2001,
            "summary": "유·무선 수단에 의한 저작물의 공중전달 및 온디맨드 공중이용제공에 관한 배타적 권리를 규정합니다.",
            "full_text": "Article 3(1): 회원국은 저작자에게 저작물의 공중이용제공을 포함하여 유·무선 수단에 의한 공중전달을 허락하거나 금지할 배타적 권리를 부여한다.",
            "commentary": "EU 디지털 저작권의 일반 조항이나 OCSSP 영역에서는 CDSM 제17조에 의해 대체·우선 적용됩니다.",
        },
        {
            "id": "CDSM_2",
            "label": "CDSM 제2조(6)",
            "title": "정의: 온라인 콘텐츠 공유 서비스 제공자",
            "group": "CDSM",
            "year": 2019,
            "summary": "대량의 저작물을 영리 목적으로 조직·촉진하는 플랫폼을 OCSSP로 정의하며 비영리 백과사전·오픈소스 저장소 등은 제외합니다.",
            "full_text": "Article 2(6): 이용자 업로드 보호 콘텐츠를 대량으로 저장·공중접근케 하고 이를 조직·영리 판촉하는 정보사회 서비스 제공자를 말한다.",
            "commentary": "CDSM 제17조의 적용 범위를 결정하는 관문 정의 조항입니다.",
        },
        {
            "id": "ECommerce_14",
            "label": "E-Commerce 제14조 / DSA 제6조",
            "title": "호스팅 서비스 책임 제한 (면책)",
            "group": "E-Commerce / DSA",
            "year": 2000,
            "summary": "수동적 호스팅 사업자가 불법성을 알지 못했고 통지 즉시 삭제한 경우 책임을 면제하는 세이프하버 조항입니다.",
            "full_text": "Article 14(1): 이용자 제공 정보를 저장하는 서비스 제공자는 불법성을 실제 인지하지 못했고 인지 즉시 차단한 경우 책임을 지지 않는다.",
            "commentary": "CDSM 제17조(3)에 의해 OCSSP의 저작권 관련 행위에는 적용이 명시적으로 배제됩니다.",
        },
        {
            "id": "CDSM_4",
            "label": "CDSM 제4조",
            "title": "상업적 텍스트·데이터 마이닝(TDM) 예외 및 Opt-out",
            "group": "CDSM",
            "year": 2019,
            "summary": "적법 접근 저작물에 대한 상업적 TDM을 허용하되 권리자가 기계 판독 가능한 방식으로 권리를 유보(Opt-out)하면 예외가 배제됩니다.",
            "full_text": "Article 4(1) & (3): TDM 목적의 복제·추출 예외를 인정하되 권리자가 기계 판독 가능 수단으로 명시적 유보한 경우 적용하지 않는다.",
            "commentary": "EU AI Act 제53조(1)(c)가 직접 인용하여 생성형 AI 학습 규제의 핵심 축을 담당합니다.",
        },
        {
            "id": "AIAct_53",
            "label": "EU AI Act 제53조",
            "title": "범용 AI(GPAI) 모델 제공자의 저작권 준수 의무",
            "group": "EU AI Act",
            "year": 2024,
            "summary": "GPAI 모델 제공자에게 CDSM 제4조(3) TDM 옵트아웃 준수 정책 수립 및 학습 데이터 요약 공개 의무를 부과합니다.",
            "full_text": "Article 53(1)(c)-(d): GPAI 제공자는 지침 2019/790 제4조(3) 권리 유보를 식별·준수할 정책을 수립하고 학습 데이터 요약을 공개해야 한다.",
            "commentary": "역외에서 학습된 AI 모델에도 EU 출시 시 준수를 요구하여 속지주의 원칙과 긴장 관계를 형성합니다.",
        },
    ],
    "edges": [
        {
            "source": "CDSM_17",
            "target": "InfoSoc_3",
            "label": "특별법으로 우선 적용 (Lex Specialis)",
            "relation_type": "lex_specialis",
            "color": "#f59e0b",
            "commentary": "OCSSP 서비스 내 이용자 업로드 콘텐츠에 대해서는 InfoSoc 제3조 대신 CDSM 제17조가 특별법으로 작동합니다.",
        },
        {
            "source": "CDSM_17",
            "target": "ECommerce_14",
            "label": "면책 조항 적용 배제 (충돌)",
            "relation_type": "conflict",
            "color": "#ef4444",
            "commentary": "CDSM 제17조(3)이 E-Commerce 제14조(1) 호스팅 면책의 적용을 명시적으로 배제합니다.",
        },
        {
            "source": "CDSM_17",
            "target": "CDSM_2",
            "label": "용어 정의 참조 (Citation)",
            "relation_type": "citation",
            "color": "#60a5fa",
            "commentary": "제17조의 수범자인 OCSSP 해당 여부는 제2조(6) 정의 및 예외 요건에 따라 결정됩니다.",
        },
        {
            "source": "AIAct_53",
            "target": "CDSM_4",
            "label": "TDM Opt-out 준수 강제 및 역외 적용",
            "relation_type": "conflict",
            "color": "#ef4444",
            "commentary": "EU AI Act 제53조가 CDSM 제4조(3) 옵트아웃 준수를 AI 규제 차원에서 강제합니다.",
        },
    ],
}

GROUP_PALETTE = [
    "#38bdf8",  # Sky Blue (CDSM 등)
    "#f87171",  # Coral Red (InfoSoc 등)
    "#34d399",  # Emerald (E-Commerce / DSA 등)
    "#c084fc",  # Purple (EU AI Act 등)
    "#fbbf24",  # Amber (CJEU Case Law 등)
    "#f472b6",  # Pink
    "#2dd4bf",  # Teal
    "#a3e635",  # Lime
]

PRESET_GROUP_COLORS = {
    "CDSM": "#38bdf8",
    "InfoSoc": "#f87171",
    "E-Commerce": "#34d399",
    "E-Commerce / DSA": "#34d399",
    "EU AI Act": "#c084fc",
    "CJEU Case Law": "#fbbf24",
}

RELATION_STYLES = {
    "lex_specialis": {
        "ko": "특별법 우선 (Lex Specialis)",
        "en": "Lex Specialis / Priority",
        "color": "#f59e0b",
        "dashes": False,
        "width": 3,
    },
    "conflict": {
        "ko": "충돌·적용 배제 (Conflict / Override)",
        "en": "Conflict / Exclusion",
        "color": "#ef4444",
        "dashes": False,
        "width": 3.5,
    },
    "exception": {
        "ko": "예외·한계 설정 (Exception / Limit)",
        "en": "Exception / Limitation",
        "color": "#10b981",
        "dashes": True,
        "width": 2.5,
    },
    "amended": {
        "ko": "개정·보완·강화 (Amended / Upgraded)",
        "en": "Amended / Strengthened",
        "color": "#a855f7",
        "dashes": False,
        "width": 2.5,
    },
    "citation": {
        "ko": "정의·인용 참조 (Citation / Reference)",
        "en": "Citation / Definition Ref",
        "color": "#60a5fa",
        "dashes": True,
        "width": 2,
    },
}


# =====================================================================
# 2. 유틸리티 함수 (데이터 로드, 정규화, 문서 파싱, Gemini 호출)
# =====================================================================
def load_default_sample() -> Dict[str, Any]:
    sample_path = Path(__file__).parent / "sample_legal_graph.json"
    if sample_path.exists():
        try:
            return json.loads(sample_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return FALLBACK_GRAPH_DATA


def infer_relation_type(edge: Dict[str, Any]) -> str:
    explicit = str(edge.get("relation_type", "")).strip().lower()
    if explicit in RELATION_STYLES:
        return explicit

    label = str(edge.get("label", "")).lower()
    color = str(edge.get("color", "")).lower()

    if any(k in label for k in ["충돌", "배제", "모순", "conflict", "exclude", "override"]) or color in ["red", "#ef4444"]:
        return "conflict"
    if any(k in label for k in ["예외", "제한", "한계", "exception", "limit", "safe"]):
        return "exception"
    if any(k in label for k in ["특별법", "우선", "specialis", "priority", "경계"]):
        return "lex_specialis"
    if any(k in label for k in ["개정", "보완", "격상", "강화", "amend", "upgrade", "modify"]):
        return "amended"
    return "citation"


def clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
    """마크다운 코드블록(```json ... ```)이 섞여 있어도 안전하게 JSON을 파싱합니다."""
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace : last_brace + 1]
    return json.loads(cleaned)


def normalize_graph_data(raw_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]]:
    """단순 스켈레톤 JSON과 확장 법률 분석 JSON을 모두 완벽하게 호환하도록 정규화합니다."""
    raw_nodes = raw_data.get("nodes", [])
    raw_edges = raw_data.get("edges", [])

    group_colors: Dict[str, str] = {}
    palette_idx = 0

    nodes: List[Dict[str, Any]] = []
    seen_ids = set()

    for idx, n in enumerate(raw_nodes):
        node_id = str(n.get("id") or f"Node_{idx + 1}").strip()
        if node_id in seen_ids:
            continue
        seen_ids.add(node_id)

        group = str(n.get("group") or "기타 법령").strip()
        if group not in group_colors:
            if group in PRESET_GROUP_COLORS:
                group_colors[group] = PRESET_GROUP_COLORS[group]
            else:
                group_colors[group] = GROUP_PALETTE[palette_idx % len(GROUP_PALETTE)]
                palette_idx += 1

        label = str(n.get("label") or node_id).strip()
        title = str(n.get("title") or label).strip()
        summary = str(n.get("summary") or title).strip()
        full_text = str(n.get("full_text") or "").strip()
        commentary = str(n.get("commentary") or "").strip()
        year = n.get("year", None)

        nodes.append(
            {
                "id": node_id,
                "label": label,
                "title": title,
                "group": group,
                "color": str(n.get("color") or group_colors[group]),
                "year": year,
                "summary": summary,
                "full_text": full_text,
                "commentary": commentary,
            }
        )

    edges: List[Dict[str, Any]] = []
    for e in raw_edges:
        src = str(e.get("source", "")).strip()
        tgt = str(e.get("target", "")).strip()
        if not src or not tgt:
            continue

        # 만약 엣지에만 등장하고 nodes 배열에 누락된 조항이 있으면 자동 생성
        for endpoint in (src, tgt):
            if endpoint not in seen_ids:
                seen_ids.add(endpoint)
                auto_group = endpoint.split("_")[0] if "_" in endpoint else "자동 추가 조항"
                if auto_group not in group_colors:
                    group_colors[auto_group] = PRESET_GROUP_COLORS.get(
                        auto_group, GROUP_PALETTE[palette_idx % len(GROUP_PALETTE)]
                    )
                    palette_idx += 1
                nodes.append(
                    {
                        "id": endpoint,
                        "label": endpoint,
                        "title": endpoint,
                        "group": auto_group,
                        "color": group_colors[auto_group],
                        "year": None,
                        "summary": "엣지 연결 관계에서 자동 감지된 조항입니다.",
                        "full_text": "",
                        "commentary": "",
                    }
                )

        rel_type = infer_relation_type(e)
        style = RELATION_STYLES[rel_type]
        rel_label = str(e.get("label") or style["ko"]).strip()
        edge_color = str(e.get("color") or style["color"]).strip()
        commentary = str(e.get("commentary") or f"'{src}' 조항과 '{tgt}' 조항 간의 '{rel_label}' 법적 연결 관계입니다.").strip()

        edges.append(
            {
                "source": src,
                "target": tgt,
                "label": rel_label,
                "relation_type": rel_type,
                "color": edge_color,
                "dashes": style["dashes"],
                "width": style["width"],
                "commentary": commentary,
            }
        )

    return nodes, edges, group_colors


def extract_text_from_uploads(uploaded_files: List[Any]) -> str:
    chunks: List[str] = []
    for f in uploaded_files:
        name = f.name.lower()
        data = f.read()
        if name.endswith(".pdf") and HAS_PYPDF:
            reader = PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            chunks.append(f"=== [FILE: {f.name}] ===\n" + "\n".join(pages))
        elif name.endswith(".docx") and HAS_DOCX:
            doc = docx.Document(io.BytesIO(data))
            paras = [p.text for p in doc.paragraphs if p.text.strip()]
            chunks.append(f"=== [FILE: {f.name}] ===\n" + "\n".join(paras))
        else:
            text = data.decode("utf-8", errors="ignore")
            chunks.append(f"=== [FILE: {f.name}] ===\n{text}")
    return "\n\n".join(chunks)


def get_api_key(user_input_key: str) -> str:
    if user_input_key and user_input_key.strip():
        return user_input_key.strip()
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "").strip()


def build_agent_extraction_prompt(law_names: str, detailed: bool = True) -> str:
    if not detailed:
        return f"""내가 올린 [{law_names}] 문서를 분석해서, 법안의 조항(Article) 간의 연관 관계를 추출해 줘.
반드시 아래의 JSON 포맷으로만 답변해야 해. 다른 부연 설명은 하지 마.

```json
{{
  "nodes": [
    {{"id": "CDSM_Art17", "label": "CDSM 제17조", "title": "플랫폼의 콘텐츠 책임", "group": "CDSM"}},
    {{"id": "InfoSoc_Art3", "label": "InfoSoc 제3조", "title": "공중전달권", "group": "InfoSoc"}}
  ],
  "edges": [
    {{"source": "CDSM_Art17", "target": "InfoSoc_Art3", "label": "특별법 우선 적용", "color": "#f59e0b"}}
  ]
}}
```"""

    return f"""내가 제공한 [{law_names}] 법률/판례 문서를 리걸테크 지식 그래프용으로 정밀 분석해 줘.
조항(Article) 및 핵심 판례 단위로 노드(nodes)와 조항 간 법적 연결 관계(edges)를 추출하되, 반드시 아래 JSON 포맷으로만 출력해. 다른 설명 문장은 절대 포함하지 마.

relation_type 허용값:
- "lex_specialis" (특별법 우선 적용)
- "conflict" (법적 충돌 / 면책 배제 / 모순)
- "exception" (예외 인정 / 권리 제한 / 합헌적 한계)
- "amended" (개정 / 보완 / 강행규정 격상)
- "citation" (용어 정의 참조 / 단순 인용)

```json
{{
  "nodes": [
    {{
      "id": "CDSM_17",
      "label": "CDSM 제17조",
      "title": "온라인 콘텐츠 공유 서비스 제공자 책임",
      "group": "CDSM",
      "year": 2019,
      "summary": "해당 조항의 핵심 법리 1~2문장 요약",
      "full_text": "조항 원문 또는 핵심 요지 발췌",
      "commentary": "다른 법률 조항과 왜 연결되며 실무상 어떤 쟁점이 있는지 전문 해설"
    }}
  ],
  "edges": [
    {{
      "source": "CDSM_17",
      "target": "InfoSoc_3",
      "label": "특별법 우선 적용 (Lex Specialis)",
      "relation_type": "lex_specialis",
      "commentary": "두 조항이 법리적으로 어떻게 연결·충돌·보완되는지 구체적 설명"
    }}
  ]
}}
```"""


def call_gemini_extract_graph(api_key: str, source_text: str, model_name: str = "gemini-2.5-flash") -> Dict[str, Any]:
    client = genai.Client(api_key=api_key)
    prompt = (
        build_agent_extraction_prompt("업로드된 법률 및 판례 문서", detailed=True)
        + "\n\n[분석 대상 법률 원문]:\n"
        + source_text[:120000]
    )
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return clean_and_parse_json(response.text)


def call_gemini_legal_research(api_key: str, task_prompt: str, model_name: str = "gemini-2.5-flash") -> str:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=task_prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return response.text or ""


# =====================================================================
# 3. 인터랙티브 Pyvis + 우측 실시간 클릭 상세창 렌더러
# =====================================================================
def render_interactive_pyvis_with_inspector(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    enable_physics: bool = True,
    directed: bool = True,
    lang: str = "ko",
) -> str:
    nx_graph = nx.DiGraph() if directed else nx.Graph()

    degree_count: Dict[str, int] = {n["id"]: 0 for n in nodes}
    for e in edges:
        degree_count[e["source"]] = degree_count.get(e["source"], 0) + 1
        degree_count[e["target"]] = degree_count.get(e["target"], 0) + 1

    for n in nodes:
        deg = degree_count.get(n["id"], 0)
        size = min(44, 22 + deg * 4)
        tooltip = f"[{n['group']}] {n['label']}\n{n['title']}"
        nx_graph.add_node(
            n["id"],
            label=n["label"],
            title=tooltip,
            color={
                "background": n["color"],
                "border": "#f8fafc",
                "highlight": {"background": n["color"], "border": "#facc15"},
                "hover": {"background": n["color"], "border": "#ffffff"},
            },
            size=size,
            shape="dot",
            borderWidth=2,
            font={"color": "#f8fafc", "size": 14, "face": "Pretendard, Segoe UI, sans-serif"},
        )

    for idx, e in enumerate(edges):
        nx_graph.add_edge(
            e["source"],
            e["target"],
            id=f"edge_{idx}",
            label=e["label"],
            title=f"{e['label']}\n{e['commentary']}",
            color={"color": e["color"], "highlight": "#facc15", "hover": "#ffffff"},
            width=e["width"],
            dashes=e["dashes"],
            font={
                "color": "#cbd5e1",
                "size": 11,
                "strokeWidth": 3,
                "strokeColor": "#0f172a",
                "align": "middle",
            },
        )

    net = Network(
        height="630px",
        width="100%",
        bgcolor="#0f172a",
        font_color="#f8fafc",
        directed=directed,
        cdn_resources="in_line",
    )
    net.from_nx(nx_graph)

    if enable_physics:
        net.repulsion(node_distance=220, central_gravity=0.15, spring_length=210, spring_strength=0.04, damping=0.09)
    else:
        net.toggle_physics(False)

    base_html = net.generate_html()

    # 안전한 JSON 직렬화 (</script> 탈출 방지)
    inspector_payload = {
        "lang": lang,
        "nodes": {n["id"]: n for n in nodes},
        "edges": [{**e, "id": f"edge_{idx}"} for idx, e in enumerate(edges)],
        "relationLabels": {
            k: (v["ko"] if lang == "ko" else v["en"]) for k, v in RELATION_STYLES.items()
        },
    }
    payload_json = json.dumps(inspector_payload, ensure_ascii=False).replace("</", "<\\/")

    fit_label = "화면 맞춤" if lang == "ko" else "Fit View"
    freeze_label = "움직임 고정/해제" if lang == "ko" else "Freeze / Unfreeze"
    empty_title = "조항 노드(원) 또는 연결선(선)을 클릭하세요" if lang == "ko" else "Click any Article Node or Edge"
    empty_desc = (
        "좌측 거미줄 그래프에서 특정 법률 조항 원(Node)을 클릭하면 조항 전문, 핵심 요약, 연결된 타 법령 목록과 에이전트의 법률 해설이 이곳에 즉시 표시됩니다."
        if lang == "ko"
        else "Click any floating Article node or relationship line on the left graph to inspect its statutory text, summary, connected provisions, and legal commentary."
    )

    custom_injection = f"""
    <style>
        html, body {{
            margin: 0 !important;
            padding: 0 !important;
            background: #0b1120 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif;
            overflow: hidden;
        }}
        body {{
            display: flex;
            gap: 14px;
            padding: 6px !important;
            height: 645px;
            box-sizing: border-box;
        }}
        .card {{
            flex: 1 1 64%;
            min-width: 0;
            margin: 0 !important;
            border: 1px solid #1e293b !important;
            border-radius: 14px !important;
            background: #0f172a !important;
            position: relative;
            overflow: hidden;
            height: 632px !important;
        }}
        #mynetwork {{
            width: 100% !important;
            height: 632px !important;
            border: none !important;
            background: radial-gradient(circle at center, #131f38 0%, #0b1120 100%) !important;
        }}
        .graph-toolbar {{
            position: absolute;
            top: 12px;
            left: 12px;
            z-index: 20;
            display: flex;
            gap: 8px;
        }}
        .graph-btn {{
            background: rgba(15, 23, 42, 0.88);
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 6px 11px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            backdrop-filter: blur(6px);
            transition: all 0.15s ease;
        }}
        .graph-btn:hover {{
            border-color: #38bdf8;
            color: #38bdf8;
        }}
        #legal-inspector {{
            flex: 0 0 35%;
            max-width: 430px;
            height: 632px;
            overflow-y: auto;
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 18px;
            color: #e2e8f0;
            box-sizing: border-box;
            box-shadow: 0 10px 25px rgba(0,0,0,0.35);
        }}
        #legal-inspector::-webkit-scrollbar {{
            width: 6px;
        }}
        #legal-inspector::-webkit-scrollbar-thumb {{
            background: #334155;
            border-radius: 3px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.3px;
            margin-right: 6px;
            margin-bottom: 6px;
        }}
        .insp-title {{
            font-size: 18px;
            font-weight: 800;
            color: #f8fafc;
            margin: 6px 0 4px 0;
            line-height: 1.35;
        }}
        .insp-subtitle {{
            font-size: 13.5px;
            color: #94a3b8;
            margin-bottom: 14px;
            line-height: 1.45;
        }}
        .insp-section {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 12px 14px;
            margin-bottom: 12px;
        }}
        .insp-section-header {{
            font-size: 11.5px;
            font-weight: 700;
            text-transform: uppercase;
            color: #38bdf8;
            margin-bottom: 6px;
            letter-spacing: 0.4px;
        }}
        .insp-text {{
            font-size: 13px;
            line-height: 1.6;
            color: #e2e8f0;
            white-space: pre-line;
        }}
        .conn-item {{
            display: block;
            width: 100%;
            text-align: left;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 9px 11px;
            margin-top: 7px;
            color: #f1f5f9;
            cursor: pointer;
            transition: border-color 0.15s ease, transform 0.1s ease;
        }}
        .conn-item:hover {{
            border-color: #38bdf8;
            transform: translateX(2px);
        }}
        .conn-rel {{
            font-size: 11px;
            font-weight: 700;
            display: block;
            margin-bottom: 2px;
        }}
        .conn-target {{
            font-size: 13px;
            font-weight: 600;
        }}
        .empty-state {{
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 18px;
            color: #94a3b8;
        }}
        .empty-icon {{
            font-size: 40px;
            margin-bottom: 12px;
        }}
    </style>

    <div id="legal-inspector">
        <div class="empty-state">
            <div class="empty-icon">⚖️</div>
            <div style="font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:8px;">{empty_title}</div>
            <div style="font-size:13px;line-height:1.6;">{empty_desc}</div>
        </div>
    </div>

    <script>
    (function() {{
        const PAYLOAD = {payload_json};
        const isKo = PAYLOAD.lang === "ko";
        let physicsOn = {'true' if enable_physics else 'false'};

        const cardEl = document.querySelector(".card");
        if (cardEl) {{
            const toolbar = document.createElement("div");
            toolbar.className = "graph-toolbar";
            toolbar.innerHTML = `
                <button class="graph-btn" id="btn-fit">🎯 {fit_label}</button>
                <button class="graph-btn" id="btn-freeze">❄️ {freeze_label}</button>
            `;
            cardEl.appendChild(toolbar);

            document.getElementById("btn-fit").addEventListener("click", function() {{
                if (typeof network !== "undefined") {{
                    network.fit({{ animation: {{ duration: 450, easingFunction: "easeInOutQuad" }} }});
                }}
            }});
            document.getElementById("btn-freeze").addEventListener("click", function() {{
                if (typeof network !== "undefined") {{
                    physicsOn = !physicsOn;
                    network.setOptions({{ physics: {{ enabled: physicsOn }} }});
                }}
            }});
        }}

        function escapeHtml(str) {{
            if (!str) return "";
            return String(str)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
        }}

        window.focusArticleNode = function(nodeId) {{
            if (typeof network !== "undefined" && PAYLOAD.nodes[nodeId]) {{
                network.selectNodes([nodeId]);
                network.focus(nodeId, {{ scale: 1.2, animation: {{ duration: 450, easingFunction: "easeInOutQuad" }} }});
                renderNodeDetail(nodeId);
            }}
        }};

        function renderNodeDetail(nodeId) {{
            const n = PAYLOAD.nodes[nodeId];
            if (!n) return;
            const inspector = document.getElementById("legal-inspector");

            const relatedEdges = PAYLOAD.edges.filter(e => e.source === nodeId || e.target === nodeId);
            let connHtml = "";
            if (relatedEdges.length > 0) {{
                connHtml = relatedEdges.map(e => {{
                    const otherId = e.source === nodeId ? e.target : e.source;
                    const otherNode = PAYLOAD.nodes[otherId] || {{ label: otherId, title: "" }};
                    const dirArrow = e.source === nodeId ? "→" : "←";
                    return `
                        <button class="conn-item" onclick="window.focusArticleNode('${{escapeHtml(otherId)}}')">
                            <span class="conn-rel" style="color:${{escapeHtml(e.color)}}">● ${{escapeHtml(e.label)}}</span>
                            <span class="conn-target">${{dirArrow}} ${{escapeHtml(otherNode.label)}} · <span style="font-weight:400;color:#94a3b8;">${{escapeHtml(otherNode.title)}}</span></span>
                        </button>
                    `;
                }}).join("");
            }} else {{
                connHtml = `<div class="insp-text" style="color:#94a3b8;">${{isKo ? "현재 필터 기준 연결된 조항이 없습니다." : "No connected provisions under current filters."}}</div>`;
            }}

            const yearBadge = n.year ? `<span class="badge" style="background:#1e293b;color:#cbd5e1;border:1px solid #475569;">${{escapeHtml(n.year)}}</span>` : "";
            const fullTextBlock = n.full_text ? `
                <div class="insp-section">
                    <div class="insp-section-header">📜 ${{isKo ? "조항 전문 / 핵심 조문" : "Statutory Text / Excerpt"}}</div>
                    <div class="insp-text">${{escapeHtml(n.full_text)}}</div>
                </div>
            ` : "";

            const commentaryBlock = n.commentary ? `
                <div class="insp-section">
                    <div class="insp-section-header">🧠 ${{isKo ? "에이전트 법률 연결 해설" : "AI Legal Commentary"}}</div>
                    <div class="insp-text">${{escapeHtml(n.commentary)}}</div>
                </div>
            ` : "";

            inspector.innerHTML = `
                <div>
                    <span class="badge" style="background:${{escapeHtml(n.color)}}22;color:${{escapeHtml(n.color)}};border:1px solid ${{escapeHtml(n.color)}};">
                        ${{escapeHtml(n.group)}}
                    </span>
                    ${{yearBadge}}
                    <div class="insp-title">${{escapeHtml(n.label)}}</div>
                    <div class="insp-subtitle">${{escapeHtml(n.title)}}</div>

                    <div class="insp-section">
                        <div class="insp-section-header">📌 ${{isKo ? "핵심 요약" : "Core Summary"}}</div>
                        <div class="insp-text">${{escapeHtml(n.summary)}}</div>
                    </div>

                    ${{fullTextBlock}}
                    ${{commentaryBlock}}

                    <div class="insp-section">
                        <div class="insp-section-header">🔗 ${{isKo ? "연결된 타 조항 (" + relatedEdges.length + ")" : "Connected Articles (" + relatedEdges.length + ")"}}</div>
                        ${{connHtml}}
                    </div>
                </div>
            `;
        }}

        function renderEdgeDetail(edgeId) {{
            const e = PAYLOAD.edges.find(item => item.id === edgeId);
            if (!e) return;
            const srcNode = PAYLOAD.nodes[e.source] || {{ label: e.source }};
            const tgtNode = PAYLOAD.nodes[e.target] || {{ label: e.target }};
            const relTypeName = PAYLOAD.relationLabels[e.relation_type] || e.relation_type;
            const inspector = document.getElementById("legal-inspector");

            inspector.innerHTML = `
                <div>
                    <span class="badge" style="background:${{escapeHtml(e.color)}}22;color:${{escapeHtml(e.color)}};border:1px solid ${{escapeHtml(e.color)}};">
                        ${{escapeHtml(relTypeName)}}
                    </span>
                    <div class="insp-title">${{escapeHtml(srcNode.label)}} → ${{escapeHtml(tgtNode.label)}}</div>
                    <div class="insp-subtitle">${{escapeHtml(e.label)}}</div>

                    <div class="insp-section">
                        <div class="insp-section-header">⚖️ ${{isKo ? "조항 간 연결·충돌 법리 해설" : "Inter-Article Relationship Analysis"}}</div>
                        <div class="insp-text">${{escapeHtml(e.commentary)}}</div>
                    </div>

                    <div class="insp-section">
                        <div class="insp-section-header">🔍 ${{isKo ? "양측 조항 바로가기" : "Inspect Linked Nodes"}}</div>
                        <button class="conn-item" onclick="window.focusArticleNode('${{escapeHtml(e.source)}}')">
                            <span class="conn-target">📍 ${{escapeHtml(srcNode.label)}} (${{escapeHtml(srcNode.title || "")}})</span>
                        </button>
                        <button class="conn-item" onclick="window.focusArticleNode('${{escapeHtml(e.target)}}')">
                            <span class="conn-target">📍 ${{escapeHtml(tgtNode.label)}} (${{escapeHtml(tgtNode.title || "")}})</span>
                        </button>
                    </div>
                </div>
            `;
        }}

        if (typeof network !== "undefined") {{
            network.on("click", function(params) {{
                if (params.nodes && params.nodes.length > 0) {{
                    renderNodeDetail(params.nodes[0]);
                }} else if (params.edges && params.edges.length > 0) {{
                    renderEdgeDetail(params.edges[0]);
                }}
            }});

            // 초기 로드 시 가장 연결이 많은 핵심 허브 노드를 자동으로 상세창에 표시
            const nodeIds = Object.keys(PAYLOAD.nodes);
            if (nodeIds.length > 0) {{
                let bestId = nodeIds[0];
                let bestDeg = -1;
                nodeIds.forEach(id => {{
                    const deg = PAYLOAD.edges.filter(e => e.source === id || e.target === id).length;
                    if (deg > bestDeg) {{
                        bestDeg = deg;
                        bestId = id;
                    }}
                }});
                renderNodeDetail(bestId);
            }}
        }}
    }})();
    </script>
    """

    if "</body>" in base_html:
        return base_html.replace("</body>", custom_injection + "\n</body>")
    return base_html + custom_injection


def render_venn_svg(node_a: Dict[str, Any], node_b: Dict[str, Any], direct_edges: List[Dict[str, Any]]) -> str:
    overlap_raw = direct_edges[0]["label"] if direct_edges else "교차 적용 / 해석상 경합 영역"
    overlap_label = html.escape(overlap_raw[:26])
    la, ga = html.escape(node_a["label"]), html.escape(node_a["group"])
    lb, gb = html.escape(node_b["label"]), html.escape(node_b["group"])
    ca, cb = html.escape(node_a["color"]), html.escape(node_b["color"])
    return f"""
    <div style="background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:18px;text-align:center;">
        <svg viewBox="0 0 680 270" style="width:100%;max-width:660px;height:auto;">
            <circle cx="245" cy="135" r="108" fill="{ca}" fill-opacity="0.26" stroke="{ca}" stroke-width="2.5"/>
            <circle cx="435" cy="135" r="108" fill="{cb}" fill-opacity="0.26" stroke="{cb}" stroke-width="2.5"/>
            <text x="180" y="115" fill="#f8fafc" font-size="15" font-weight="700" text-anchor="middle">{la}</text>
            <text x="180" y="140" fill="#cbd5e1" font-size="11.5" text-anchor="middle">{ga}</text>
            <text x="500" y="115" fill="#f8fafc" font-size="15" font-weight="700" text-anchor="middle">{lb}</text>
            <text x="500" y="140" fill="#cbd5e1" font-size="11.5" text-anchor="middle">{gb}</text>
            <text x="340" y="128" fill="#fde047" font-size="12.5" font-weight="700" text-anchor="middle">교차·경합 영역</text>
            <text x="340" y="150" fill="#f8fafc" font-size="11" text-anchor="middle">{overlap_label}</text>
        </svg>
    </div>
    """


# =====================================================================
# 4. 세션 상태 초기화 및 사이드바 컨트롤
# =====================================================================
if "graph_raw" not in st.session_state:
    st.session_state["graph_raw"] = load_default_sample()

with st.sidebar:
    st.markdown("## ⚖️ LegalGraph Studio")
    lang_choice = st.radio(
        "언어 / Language",
        options=["한국어", "English"],
        horizontal=True,
    )
    lang = "ko" if lang_choice == "한국어" else "en"

    st.divider()
    st.markdown("### 📂 1. 법률 데이터 소스" if lang == "ko" else "### 📂 1. Legal Data Source")
    source_mode = st.radio(
        "데이터 입력 방식 선택" if lang == "ko" else "Choose input mode",
        options=[
            "📚 기본 샘플 (EU 저작권·AI·플랫폼법)",
            "📋 에이전트 JSON 붙여넣기 / 업로드",
            "🤖 법률 문서 업로드 → Gemini 자동 추출",
        ],
    )

    user_api_key = st.text_input(
        "🔑 Gemini API Key (선택 / 자동추출·AI분석용)",
        type="password",
        help="NotebookLM 등에서 만든 JSON만 시각화할 때는 API 키가 없어도 모든 그래프 기능이 100% 작동합니다.",
    )
    active_api_key = get_api_key(user_api_key)

    if source_mode.startswith("📚"):
        if st.button("🔄 기본 샘플 데이터 다시 불러오기", use_container_width=True):
            st.session_state["graph_raw"] = load_default_sample()

    elif source_mode.startswith("📋"):
        uploaded_json = st.file_uploader("JSON 파일 업로드 (.json)", type=["json"])
        if uploaded_json is not None:
            try:
                parsed = clean_and_parse_json(uploaded_json.read().decode("utf-8"))
                st.session_state["graph_raw"] = parsed
                st.success("JSON 파일이 성공적으로 반영되었습니다!")
            except Exception as exc:
                st.error(f"JSON 파싱 오류: {exc}")

        pasted_json = st.text_area(
            "또는 NotebookLM / 에이전트가 생성한 JSON 붙여넣기",
            height=170,
            placeholder='{"nodes": [...], "edges": [...]}',
        )
        if st.button("✅ 붙여넣은 JSON 그래프에 적용", use_container_width=True, type="primary"):
            if pasted_json.strip():
                try:
                    st.session_state["graph_raw"] = clean_and_parse_json(pasted_json)
                    st.success("그래프 데이터가 업데이트되었습니다!")
                except Exception as exc:
                    st.error(f"JSON 형식을 확인해 주세요: {exc}")

    elif source_mode.startswith("🤖"):
        uploaded_docs = st.file_uploader(
            "법령/판례 파일 업로드 (PDF, DOCX, TXT, MD)",
            type=["pdf", "docx", "txt", "md"],
            accept_multiple_files=True,
        )
        raw_law_paste = st.text_area(
            "또는 법률 조문 텍스트 직접 붙여넣기",
            height=130,
            placeholder="분석할 법령 조항이나 판례 요지를 붙여넣으세요...",
        )
        if st.button("🚀 Gemini로 조항 관계 자동 추출", use_container_width=True, type="primary"):
            if not HAS_GENAI:
                st.error("`google-genai` 패키지가 설치되어 있지 않습니다.")
            elif not active_api_key:
                st.warning("상단에 Gemini API Key를 먼저 입력해 주세요.")
            else:
                combined_text = ""
                if uploaded_docs:
                    combined_text += extract_text_from_uploads(uploaded_docs)
                if raw_law_paste.strip():
                    combined_text += "\n\n" + raw_law_paste.strip()
                if not combined_text.strip():
                    st.warning("업로드된 문서나 텍스트가 없습니다.")
                else:
                    with st.spinner("Gemini가 법령 간 인용·예외·충돌 관계를 추출하고 있습니다..."):
                        try:
                            extracted = call_gemini_extract_graph(active_api_key, combined_text)
                            st.session_state["graph_raw"] = extracted
                            st.success(
                                f"추출 완료! 조항 {len(extracted.get('nodes', []))}개, 관계 {len(extracted.get('edges', []))}개"
                            )
                        except Exception as exc:
                            st.error(f"Gemini 추출 중 오류 발생: {exc}")

    # 데이터 정규화 후 필터 구성
    all_nodes, all_edges, group_colors = normalize_graph_data(st.session_state["graph_raw"])
    all_groups = sorted(list({n["group"] for n in all_nodes}))

    st.divider()
    st.markdown("### 🎛️ 2. 법령 및 관계 필터링" if lang == "ko" else "### 🎛️ 2. Graph Filters")

    selected_groups = st.multiselect(
        "표시할 법령/판례 그룹 (Statutes)",
        options=all_groups,
        default=all_groups,
    )

    rel_options = list(RELATION_STYLES.keys())
    selected_relations = st.multiselect(
        "법적 관계 유형 필터 (Relation Types)",
        options=rel_options,
        default=rel_options,
        format_func=lambda k: RELATION_STYLES[k]["ko"] if lang == "ko" else RELATION_STYLES[k]["en"],
    )

    search_keyword = st.text_input(
        "🔎 특정 조항/키워드 검색 필터",
        placeholder="예: 제17조, TDM, 면책, AI...",
    )

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        enable_physics = st.checkbox("거미줄 물리효과", value=True)
    with col_opt2:
        show_arrows = st.checkbox("방향 화살표", value=True)


# =====================================================================
# 5. 필터 적용 및 메인 화면 렌더링
# =====================================================================
filtered_nodes = [n for n in all_nodes if n["group"] in selected_groups]
if search_keyword.strip():
    kw = search_keyword.strip().lower()
    matched_ids = {
        n["id"]
        for n in filtered_nodes
        if kw in n["label"].lower()
        or kw in n["title"].lower()
        or kw in n["summary"].lower()
        or kw in n["full_text"].lower()
    }
    # 검색된 노드와 직접 연결된 1촌 노드까지 함께 보여주어 맥락 유지
    neighbor_ids = set(matched_ids)
    for e in all_edges:
        if e["relation_type"] in selected_relations:
            if e["source"] in matched_ids:
                neighbor_ids.add(e["target"])
            if e["target"] in matched_ids:
                neighbor_ids.add(e["source"])
    filtered_nodes = [n for n in filtered_nodes if n["id"] in neighbor_ids]

allowed_node_ids = {n["id"] for n in filtered_nodes}
filtered_edges = [
    e
    for e in all_edges
    if e["source"] in allowed_node_ids
    and e["target"] in allowed_node_ids
    and e["relation_type"] in selected_relations
]

# 상단 헤더
st.title("⚖️ 법률 조항 교차 시각화 & 리걸테크 분석 앱")
st.caption(
    "Network Knowledge Graph 기반 다중 법령·판례 조항(Article-to-Article) 연계 탐색 및 AI 법률 리서치 스튜디오"
)

# 핵심 지표 카드
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("표시된 법령/판례 수", f"{len({n['group'] for n in filtered_nodes})}개")
kpi2.metric("분석 조항(Node) 수", f"{len(filtered_nodes)}개")
kpi3.metric("법적 연결(Edge) 수", f"{len(filtered_edges)}개")

hub_label = "-"
if filtered_nodes:
    deg_map = {n["id"]: 0 for n in filtered_nodes}
    for e in filtered_edges:
        deg_map[e["source"]] = deg_map.get(e["source"], 0) + 1
        deg_map[e["target"]] = deg_map.get(e["target"], 0) + 1
    top_id = max(deg_map, key=lambda k: deg_map[k])
    top_node = next((n for n in filtered_nodes if n["id"] == top_id), None)
    if top_node:
        hub_label = f"{top_node['label']} ({deg_map[top_id]}건)"
kpi4.metric("핵심 허브 조항 (Hub)", hub_label)

# 메인 탭 구성
tab_graph, tab_research, tab_prompt = st.tabs(
    [
        "🕸️ 조항 연계 지식 그래프 (Network Map)",
        "🧠 AI 법률 분석 두뇌 (4대 리서치 기능)",
        "🧩 에이전트 프롬프트 & JSON 스튜디오",
    ]
)

# ---------------------------------------------------------------------
# TAB 1: 네트워크 지식 그래프 + 실시간 클릭 상세창
# ---------------------------------------------------------------------
with tab_graph:
    if not filtered_nodes:
        st.warning("현재 선택된 필터 조건에 해당하는 법률 조항이 없습니다. 좌측 사이드바 필터를 조정해 주세요.")
    else:
        graph_html = render_interactive_pyvis_with_inspector(
            nodes=filtered_nodes,
            edges=filtered_edges,
            enable_physics=enable_physics,
            directed=show_arrows,
            lang=lang,
        )
        components.html(graph_html, height=655, scrolling=False)

        # 하단 법령 그룹 & 연결선 범례 바
        leg_col1, leg_col2 = st.columns([1.2, 1.8])
        with leg_col1:
            st.markdown("##### 📚 법령/판례 노드 범례 (Statute Groups)")
            badges_html = " ".join(
                [
                    f"<span style='display:inline-block;padding:4px 10px;margin:3px;border-radius:999px;"
                    f"background:{color}22;color:{color};border:1px solid {color};font-size:12.5px;font-weight:600;'>"
                    f"● {grp}</span>"
                    for grp, color in group_colors.items()
                    if grp in selected_groups
                ]
            )
            st.markdown(badges_html, unsafe_allow_html=True)

        with leg_col2:
            st.markdown("##### 🔗 법적 관계선 범례 (Edge Relation Styles)")
            rel_badges_html = " ".join(
                [
                    f"<span style='display:inline-block;padding:4px 10px;margin:3px;border-radius:8px;"
                    f"background:#1e293b;color:{meta['color']};border:1px {'dashed' if meta['dashes'] else 'solid'} {meta['color']};"
                    f"font-size:12px;font-weight:600;'>"
                    f"{'╌╌' if meta['dashes'] else '━━'} {meta['ko'] if lang == 'ko' else meta['en']}</span>"
                    for rkey, meta in RELATION_STYLES.items()
                    if rkey in selected_relations
                ]
            )
            st.markdown(rel_badges_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# TAB 2: 4대 리걸테크 심층 리서치 스튜디오
# ---------------------------------------------------------------------
with tab_research:
    st.markdown("### 🧠 파이썬 법률 분석 두뇌 스튜디오")
    st.caption(
        "그래프에 로드된 법률 조항 데이터를 기반으로 교차 비교, 충돌·허점 탐지, 입법·판례 흐름 추적, 파트너 보고용 법률 메모 초안을 생성합니다."
    )

    research_mode = st.radio(
        "분석 모듈 선택",
        options=[
            "1️⃣ 다중 법령 교차 분석 (벤 다이어그램)",
            "2️⃣ 법적 충돌 및 사각지대(Gap) 탐지",
            "3️⃣ 입법 연혁 및 판례 흐름 추적",
            "4️⃣ 맞춤형 법률 검토 메모(Memo) 작성",
        ],
        horizontal=True,
    )

    node_map = {n["id"]: n for n in all_nodes}
    node_ids = [n["id"] for n in all_nodes]

    # 1. 벤 다이어그램 교차 비교
    if research_mode and research_mode.startswith("1️⃣"):
        if len(node_ids) < 2:
            st.info("교차 비교를 위해 최소 2개 이상의 조항 노드가 필요합니다.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                id_a = st.selectbox(
                    "비교 조항 A 선택",
                    options=node_ids,
                    index=0,
                    format_func=lambda x: f"[{node_map[x]['group']}] {node_map[x]['label']} - {node_map[x]['title']}",
                )
            with c2:
                default_b = 1 if len(node_ids) > 1 else 0
                id_b = st.selectbox(
                    "비교 조항 B 선택",
                    options=node_ids,
                    index=default_b,
                    format_func=lambda x: f"[{node_map[x]['group']}] {node_map[x]['label']} - {node_map[x]['title']}",
                )

            na, nb = node_map[id_a], node_map[id_b]
            direct_links = [
                e
                for e in all_edges
                if (e["source"] == id_a and e["target"] == id_b)
                or (e["source"] == id_b and e["target"] == id_a)
            ]

            st.markdown(render_venn_svg(na, nb, direct_links), unsafe_allow_html=True)

            comp_col1, comp_col2, comp_col3 = st.columns(3)
            with comp_col1:
                st.markdown(f"#### 🟦 {na['label']} 독자 영역")
                st.write(f"**소속 법령:** {na['group']}")
                st.write(f"**핵심 요지:** {na['summary']}")
                if na["full_text"]:
                    st.caption(na["full_text"])
            with comp_col2:
                st.markdown("#### 🟨 교차 적용 · 경합 영역")
                if direct_links:
                    for dl in direct_links:
                        st.warning(f"**{dl['label']}**\n\n{dl['commentary']}")
                else:
                    st.info("두 조항 간 직접 연결선(1촌 엣지)은 없으나, 간접 경로 또는 상위 법리를 통해 교차 해석될 수 있습니다.")
            with comp_col3:
                st.markdown(f"#### 🟥 {nb['label']} 독자 영역")
                st.write(f"**소속 법령:** {nb['group']}")
                st.write(f"**핵심 요지:** {nb['summary']}")
                if nb["full_text"]:
                    st.caption(nb["full_text"])

            if st.button("✨ Gemini로 두 조항 정밀 비교 분석 실행", key="btn_venn_ai"):
                if not active_api_key:
                    st.warning("좌측 사이드바에 Gemini API Key를 입력하면 실시간 심층 비교 보고서가 생성됩니다.")
                else:
                    prompt = (
                        f"다음 두 법률 조항의 적용 범위를 벤 다이어그램 관점(1. {na['label']}만의 적용 영역, "
                        f"2. {nb['label']}만의 적용 영역, 3. 공통 교차/충돌 영역 및 실무상 우선순위)으로 한국어 법률 전문가 수준에서 비교 분석해 줘.\n\n"
                        f"[조항 A]: {json.dumps(na, ensure_ascii=False)}\n"
                        f"[조항 B]: {json.dumps(nb, ensure_ascii=False)}\n"
                        f"[기존 연결 정보]: {json.dumps(direct_links, ensure_ascii=False)}"
                    )
                    with st.spinner("교차 법리 분석 중..."):
                        st.markdown(call_gemini_legal_research(active_api_key, prompt))

    # 2. 법적 충돌 및 허점 탐지
    elif research_mode and research_mode.startswith("2️⃣"):
        conflict_edges = [e for e in all_edges if e["relation_type"] in ("conflict", "exception", "lex_specialis")]
        st.markdown(f"#### 🚨 그래프 내 자동 탐지된 충돌·예외·우선적용 지점 ({len(conflict_edges)}건)")
        for ce in conflict_edges:
            s_lbl = node_map.get(ce["source"], {}).get("label", ce["source"])
            t_lbl = node_map.get(ce["target"], {}).get("label", ce["target"])
            badge_name = RELATION_STYLES[ce["relation_type"]]["ko"]
            with st.expander(f"⚠️ [{badge_name}] {s_lbl} ↔ {t_lbl} : {ce['label']}", expanded=True):
                st.write(ce["commentary"])

        focus_question = st.text_input(
            "추가로 탐지할 법적 사각지대(Gap) 주제 지정 (선택)",
            value="생성형 AI 학습 및 플랫폼 책임 적용 시 발생하는 모순점과 입법적 사각지대",
        )
        if st.button("🔍 Gemini로 법적 모순점 및 사각지대(Gap) 심층 진단", key="btn_gap_ai"):
            if not active_api_key:
                st.warning("좌측 사이드바에 Gemini API Key를 입력해 주세요.")
            else:
                prompt = (
                    f"아래 법률 지식 그래프 데이터를 바탕으로 '{focus_question}' 관점에서 "
                    f"1) 명시적 규범 충돌, 2) 해석상 회색지대(Legal Gap), 3) 기업/실무자가 주의해야 할 컴플라이언스 리스크를 체계적으로 도출해 줘.\n\n"
                    f"데이터: {json.dumps({'nodes': all_nodes, 'edges': all_edges}, ensure_ascii=False)}"
                )
                with st.spinner("법적 충돌 및 사각지대 진단 중..."):
                    st.markdown(call_gemini_legal_research(active_api_key, prompt))

    # 3. 입법 연혁 및 판례 흐름 추적
    elif research_mode and research_mode.startswith("3️⃣"):
        dated_nodes = sorted(
            [n for n in all_nodes if n.get("year")],
            key=lambda x: int(x["year"]),
        )
        undated_nodes = [n for n in all_nodes if not n.get("year")]

        st.markdown("#### ⏳ 입법 연혁 및 주요 판례 타임라인")
        if dated_nodes:
            for dn in dated_nodes:
                st.markdown(
                    f"""
                    <div style="border-left:3px solid {dn['color']};padding:8px 16px;margin:10px 0;background:#111827;border-radius:0 10px 10px 0;">
                        <span style="color:{dn['color']};font-weight:800;font-size:14px;">{dn['year']}년 · {dn['group']}</span>
                        <div style="font-size:16px;font-weight:700;color:#f8fafc;margin-top:2px;">{dn['label']} — {dn['title']}</div>
                        <div style="font-size:13.5px;color:#cbd5e1;margin-top:4px;">{dn['summary']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("현재 JSON 데이터에 연도(`year`) 필드가 없어 전체 조항 목록을 기준으로 연혁을 추론할 수 있습니다.")

        if undated_nodes:
            st.caption("연도 미지정 조항: " + ", ".join(n["label"] for n in undated_nodes))

        if st.button("📜 Gemini로 시대순 법리 변천사 정리", key="btn_timeline_ai"):
            if not active_api_key:
                st.warning("좌측 사이드바에 Gemini API Key를 입력해 주세요.")
            else:
                prompt = (
                    "다음 법률 조항 및 판례 데이터를 시간순·발전 단계별로 정리하여, 과거 법리가 최신 입법/판례를 거치며 어떻게 수정·강화·전환되었는지 일목요연하게 해설해 줘.\n\n"
                    f"데이터: {json.dumps({'nodes': all_nodes, 'edges': all_edges}, ensure_ascii=False)}"
                )
                with st.spinner("입법 및 판례 흐름 정리 중..."):
                    st.markdown(call_gemini_legal_research(active_api_key, prompt))

    # 4. 파트너 변호사 보고용 법률 메모 초안
    elif research_mode and research_mode.startswith("4️⃣"):
        st.markdown("#### 📝 파트너 변호사 / 의사결정권자 보고용 법률 검토 메모 생성")
        memo_issue = st.text_input(
            "검토 대상 사안 (Issue / Client Scenario)",
            value="글로벌 AI·콘텐츠 플랫폼의 EU 서비스 운영 시 저작권 면책 요건 및 TDM 옵트아웃 준수 전략",
        )

        # API 키가 없을 때도 즉시 구조화된 초안 템플릿 제공
        default_memo = f"""# 법률 검토 보고서 (Legal Review Memorandum)

- **수신:** 담당 파트너 변호사
- **발신:** 리걸테크 AI 분석팀
- **검토 주제:** {memo_issue}
- **근거 법령/판례 수:** 총 {len(all_nodes)}개 조항 / {len(all_edges)}개 교차 법리 관계

---

## I. 쟁점의 요약 (Issue Presented)
본 보고서는 **{memo_issue}**와 관련하여, 다중 법령({", ".join(all_groups)}) 간의 적용 우선순위, 면책 배제 리스크 및 실무 대응 방안을 검토합니다.

## II. 관련 핵심 법령 및 조항 구조 (Applicable Statutory Framework)
""" + "\n".join(
            [f"- **{n['label']} ({n['title']}):** {n['summary']}" for n in all_nodes]
        ) + """

## III. 조항 간 교차 적용 및 충돌 분석 (Cross-Statutory Analysis)
""" + "\n".join(
            [
                f"- **{node_map.get(e['source'], {}).get('label', e['source'])} → {node_map.get(e['target'], {}).get('label', e['target'])} ({e['label']}):** {e['commentary']}"
                for e in all_edges
            ]
        ) + """

## IV. 실무상 권고 및 결론 (Conclusion & Action Items)
1. **특별법 우선 적용 구간 점검:** 일반 호스팅 면책에 의존하기보다 특별법상 사전 라이선스·최선의 노력(Best Efforts) 입증 체계를 구축해야 합니다.
2. **기계 판독 가능 옵트아웃(TDM Opt-out) 프로토콜 준수:** 데이터 수집 및 모델 학습 파이프라인에서 권리 유보 신호 식별 로그를 보존해야 합니다.
3. **이용자 기본권 보호 안전장치 마련:** 자동화된 필터링 적용 시 인용·비평·패러디 등 적법 이용이 과잉 차단되지 않도록 이의제기 절차를 병행해야 합니다.
"""

        if "generated_memo" not in st.session_state:
            st.session_state["generated_memo"] = default_memo

        col_m1, col_m2 = st.columns([1, 1])
        with col_m1:
            if st.button("📋 현재 그래프 데이터로 기본 보고서 갱신", use_container_width=True):
                st.session_state["generated_memo"] = default_memo
        with col_m2:
            if st.button("🤖 Gemini로 심층 2페이지 법률 메모 작성", type="primary", use_container_width=True):
                if not active_api_key:
                    st.warning("Gemini 심층 작성을 위해서는 좌측 사이드바에 API Key를 입력해 주세요. (기본 구조화 초안은 아래에서 바로 확인·다운로드 가능합니다!)")
                else:
                    prompt = (
                        f"파트너 변호사에게 보고할 분량(A4 약 2장 수준)의 격식 있고 치밀한 한국어 법률 검토 보고서(Legal Memorandum)를 작성해 줘.\n"
                        f"검토 사안: {memo_issue}\n"
                        f"반드시 포함할 목차: 1. 질문 요지(Question Presented), 2. 결론 요약(Brief Answer), "
                        f"3. 관련 법령 체계 및 조항 간 관계 분석(Statutory Network Analysis), 4. 법적 충돌·사각지대 평가, 5. 실무 대응 제언.\n\n"
                        f"근거 그래프 데이터: {json.dumps({'nodes': all_nodes, 'edges': all_edges}, ensure_ascii=False)}"
                    )
                    with st.spinner("파트너 보고용 법률 검토 메모 작성 중..."):
                        st.session_state["generated_memo"] = call_gemini_legal_research(active_api_key, prompt)

        st.markdown(st.session_state["generated_memo"])
        st.download_button(
            label="📥 법률 검토 메모 다운로드 (.md)",
            data=st.session_state["generated_memo"].encode("utf-8"),
            file_name="legal_review_memo.md",
            mime="text/markdown",
        )


# ---------------------------------------------------------------------
# TAB 3: 에이전트 프롬프트 생성기 & JSON 스튜디오
# ---------------------------------------------------------------------
with tab_prompt:
    st.markdown("### 🧩 1단계: 에이전트 / NotebookLM용 JSON 추출 프롬프트 생성기")
    st.info(
        "NotebookLM, Gemini, ChatGPT 또는 로컬 파이썬 에이전트에 법률 문서를 넣은 뒤 아래 프롬프트를 그대로 복사해 입력하면, 본 시각화 앱과 100% 호환되는 JSON 데이터를 즉시 얻을 수 있습니다."
    )

    p_col1, p_col2 = st.columns([2, 1])
    with p_col1:
        target_laws = st.text_input(
            "분석할 법령/판례 이름 입력",
            value="CDSM 지침, InfoSoc 지침, EU AI Act",
        )
    with p_col2:
        prompt_level = st.radio(
            "프롬프트 상세도",
            options=["심층 법률해설 포함 (권장)", "초간단 기초 스켈레톤"],
        )

    generated_prompt = build_agent_extraction_prompt(
        target_laws,
        detailed=prompt_level.startswith("심층"),
    )
    st.code(generated_prompt, language="markdown")

    st.divider()
    st.markdown("### 🗂️ 2단계: 현재 활성화된 그래프 JSON 확인 및 다운로드")
    pretty_current_json = json.dumps(st.session_state["graph_raw"], ensure_ascii=False, indent=2)
    st.download_button(
        label="💾 현재 그래프 데이터 JSON 다운로드 (legal_graph.json)",
        data=pretty_current_json.encode("utf-8"),
        file_name="legal_graph.json",
        mime="application/json",
    )
    with st.expander("현재 로드된 원본 JSON 코드 보기"):
        st.code(pretty_current_json, language="json")
