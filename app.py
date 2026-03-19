import streamlit as st
import anthropic
import base64
import json
from datetime import datetime

# ───────────────────────────────────────────
# 페이지 설정
# ───────────────────────────────────────────
st.set_page_config(
    page_title="재진님 AI 비서",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ───────────────────────────────────────────
# 스타일
# ───────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
        padding: 20px 28px;
        border-radius: 14px;
        margin-bottom: 24px;
        color: white;
    }
    .main-header h1 { margin: 0; font-size: 1.6rem; }
    .main-header p  { margin: 6px 0 0; opacity: 0.85; font-size: 0.95rem; }

    .result-box {
        background: #f0f7ff;
        border-left: 4px solid #2d6a9f;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 12px 0;
    }
    .result-box h4 { color: #1e3a5f; margin: 0 0 8px; }

    .badge {
        display: inline-block;
        background: #e8f4fd;
        color: #1e5f99;
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 2px;
    }
    .stButton > button {
        background: #2d6a9f;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        width: 100%;
    }
    .stButton > button:hover { background: #1e5a8f; }
</style>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────
# 헤더
# ───────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🤖 재진님 AI 비서</h1>
  <p>PDF · 이메일 · 도면 자료를 분석하고 영어 대응 가이드를 드립니다</p>
</div>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────
# 사이드바 — API 키
# ───────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    api_key = st.text_input(
        "Claude API 키",
        type="password",
        placeholder="sk-ant-api...",
        help="Anthropic Console에서 발급받은 API 키를 입력하세요."
    )
    st.markdown("---")
    st.markdown("**모드 선택**")
    mode = st.radio(
        "",
        ["📄 문서 요약", "🎤 회의 코치", "🖼️ 도면·이미지 분석"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown(
        "🔑 API 키 발급: [console.anthropic.com](https://console.anthropic.com)",
        unsafe_allow_html=True
    )

# ───────────────────────────────────────────
# API 클라이언트 초기화
# ───────────────────────────────────────────
def get_client():
    key = api_key or st.secrets.get("ANTHROPIC_API_KEY", "")
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)

# ───────────────────────────────────────────
# 모드 1 — 문서 요약
# ───────────────────────────────────────────
if "📄 문서 요약" in mode:
    st.subheader("📄 문서 요약기")
    st.caption("PDF를 업로드하거나 이메일/텍스트를 붙여넣으세요")

    tab1, tab2 = st.tabs(["📁 PDF 업로드", "📋 텍스트 붙여넣기"])

    content_data = None   # (type, data) — "text" or "pdf_b64"

    with tab1:
        uploaded = st.file_uploader("PDF 파일 선택", type=["pdf"])
        if uploaded:
            pdf_bytes = uploaded.read()
            pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
            content_data = ("pdf", pdf_b64)
            st.success(f"✅ {uploaded.name} 업로드 완료 ({len(pdf_bytes)//1024} KB)")

    with tab2:
        raw_text = st.text_area(
            "이메일 또는 회의록 내용을 여기에 붙여넣으세요",
            height=220,
            placeholder="예) Dear Jaejin, Please find attached the updated SIE requirements..."
        )
        if raw_text.strip():
            content_data = ("text", raw_text.strip())

    context_note = st.text_area(
        "📌 추가 맥락 (선택)",
        height=80,
        placeholder="예) 이 이메일은 Tesla SEMI 서스펜션 부품 공급 관련 내용입니다."
    )

    col_a, col_b = st.columns([3, 1])
    with col_a:
        lang_out = st.selectbox("출력 언어", ["한국어 (기본)", "한국어 + 영어 병기"])
    with col_b:
        run_btn = st.button("🚀 분석 실행", use_container_width=True)

    if run_btn:
        if not content_data:
            st.warning("PDF를 업로드하거나 텍스트를 입력해주세요.")
        elif not (api_key or st.secrets.get("ANTHROPIC_API_KEY")):
            st.error("왼쪽 사이드바에 Claude API 키를 입력해주세요.")
        else:
            client = get_client()
            bilingual = "병기" in lang_out

            system_prompt = f"""당신은 자동차 부품 공급망(APQP/SIE) 전문 분석 비서입니다.
사용자의 문서를 분석하고 아래 형식의 JSON만 반환하세요. 다른 말은 하지 마세요.
{{
  "title": "문서 제목 또는 주제 (20자 이내)",
  "summary": "전체 내용을 3-5문장으로 요약",
  "key_points": ["핵심 포인트 1", "핵심 포인트 2", ...],
  "action_items": ["조치 필요 항목 1", "조치 필요 항목 2", ...],
  "urgency": "높음|보통|낮음",
  "suggested_reply": "영어 답변 초안 (3-4문장)",
  "suggested_reply_kr": "위 영어 답변의 한국어 해석"
}}
{'모든 항목을 한국어와 영어로 병기하세요.' if bilingual else '모든 항목을 한국어로 작성하세요.'}
추가 맥락: {context_note if context_note else '없음'}"""

            with st.spinner("🔍 AI가 분석 중입니다..."):
                try:
                    if content_data[0] == "pdf":
                        messages = [{
                            "role": "user",
                            "content": [
                                {
                                    "type": "document",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "application/pdf",
                                        "data": content_data[1],
                                    }
                                },
                                {"type": "text", "text": "위 문서를 분석해주세요."}
                            ]
                        }]
                    else:
                        messages = [{
                            "role": "user",
                            "content": f"다음 내용을 분석해주세요:\n\n{content_data[1]}"
                        }]

                    response = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=2000,
                        system=system_prompt,
                        messages=messages,
                    )

                    raw = response.content[0].text.strip()
                    # JSON 파싱
                    clean = raw.replace("```json", "").replace("```", "").strip()
                    result = json.loads(clean)

                    # ── 결과 출력 ──
                    st.success("✅ 분석 완료!")

                    urgency_color = {"높음": "🔴", "보통": "🟡", "낮음": "🟢"}.get(result.get("urgency","보통"), "🟡")
                    st.markdown(f"## {result.get('title','분석 결과')}  {urgency_color} 긴급도: {result.get('urgency','보통')}")

                    st.markdown("### 📝 요약")
                    st.info(result.get("summary", ""))

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### 💡 핵심 포인트")
                        for pt in result.get("key_points", []):
                            st.markdown(f"- {pt}")
                    with col2:
                        st.markdown("### ✅ 조치 필요 항목")
                        for ai in result.get("action_items", []):
                            st.markdown(f"- {ai}")

                    st.markdown("### ✉️ 추천 영어 답변")
                    reply = result.get("suggested_reply", "")
                    st.code(reply, language=None)
                    st.caption(f"🇰🇷 해석: {result.get('suggested_reply_kr','')}")

                    # 복사용 다운로드
                    report = f"""[분석 결과] {datetime.now().strftime('%Y-%m-%d %H:%M')}
제목: {result.get('title','')}
긴급도: {result.get('urgency','')}

[요약]
{result.get('summary','')}

[핵심 포인트]
{chr(10).join('- '+p for p in result.get('key_points',[]))}

[조치 항목]
{chr(10).join('- '+a for a in result.get('action_items',[]))}

[추천 영어 답변]
{reply}

[한국어 해석]
{result.get('suggested_reply_kr','')}
"""
                    st.download_button("📥 결과 다운로드 (.txt)", report,
                                       file_name=f"분석결과_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")

                except json.JSONDecodeError:
                    st.warning("결과를 구조화하지 못했습니다. 원문을 표시합니다.")
                    st.markdown(raw)
                except Exception as e:
                    st.error(f"오류 발생: {e}")

# ───────────────────────────────────────────
# 모드 2 — 회의 코치
# ───────────────────────────────────────────
elif "🎤 회의 코치" in mode:
    st.subheader("🎤 실시간 회의 코치")
    st.caption("회의 중 들은 내용을 그대로 붙여넣으면 번역·분석·답변 가이드를 드립니다")

    transcript = st.text_area(
        "회의 내용 (영어 또는 한국어)",
        height=250,
        placeholder='예) Customer: "We found inconsistency in your durability test data. Can you explain?"'
    )
    context2 = st.text_area("📌 배경 설명 (선택)", height=70,
                             placeholder="예) Tesla SEMI Tie Rod 1차 감사 회의 중")

    if st.button("🎯 코치 분석 시작"):
        if not transcript.strip():
            st.warning("회의 내용을 입력해주세요.")
        elif not (api_key or st.secrets.get("ANTHROPIC_API_KEY")):
            st.error("사이드바에 API 키를 입력해주세요.")
        else:
            client = get_client()
            with st.spinner("분석 중..."):
                try:
                    prompt = f"""당신은 자동차 부품 공급망 전문 회의 코치입니다.
아래 회의 내용을 분석하고 JSON만 반환하세요:
{{
  "situation": "현재 상황 요약 (2-3문장)",
  "customer_concern": "고객의 핵심 우려사항",
  "our_position": "우리 측 대응 방향 제안",
  "reply_options": [
    {{"label": "신중한 답변", "english": "...", "korean": "..."}},
    {{"label": "적극적 답변", "english": "...", "korean": "..."}},
    {{"label": "확인 요청 답변", "english": "...", "korean": "..."}}
  ],
  "caution": "주의사항 또는 피해야 할 표현"
}}

배경: {context2 if context2 else '없음'}
회의 내용:
{transcript}"""

                    resp = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    raw = resp.content[0].text.strip().replace("```json","").replace("```","").strip()
                    r = json.loads(raw)

                    st.success("✅ 분석 완료!")
                    st.markdown(f"**📊 상황:** {r.get('situation','')}")
                    st.markdown(f"**⚠️ 고객 우려:** {r.get('customer_concern','')}")
                    st.markdown(f"**🎯 대응 방향:** {r.get('our_position','')}")
                    st.markdown("---")
                    st.markdown("### 💬 추천 답변 3가지")
                    for opt in r.get("reply_options", []):
                        with st.expander(f"✉️ {opt.get('label','')}"):
                            st.code(opt.get("english",""), language=None)
                            st.caption(f"🇰🇷 {opt.get('korean','')}")
                    if r.get("caution"):
                        st.warning(f"⚠️ 주의: {r.get('caution')}")

                except Exception as e:
                    st.error(f"오류: {e}")

# ───────────────────────────────────────────
# 모드 3 — 도면·이미지 분석
# ───────────────────────────────────────────
else:
    st.subheader("🖼️ 도면·이미지 분석")
    st.caption("도면 캡처, 사진, 스크린샷을 업로드하면 내용을 분석하고 기술 답변을 드립니다")

    img_file = st.file_uploader("이미지 업로드 (JPG, PNG, WEBP)", type=["jpg","jpeg","png","webp"])
    question = st.text_area("❓ 이 이미지에 대해 무엇이 궁금하신가요?",
                             height=100,
                             placeholder="예) 이 도면에서 Tie Rod 연결부의 규격을 확인해주세요.")

    if st.button("🔍 이미지 분석"):
        if not img_file:
            st.warning("이미지를 업로드해주세요.")
        elif not question.strip():
            st.warning("질문을 입력해주세요.")
        elif not (api_key or st.secrets.get("ANTHROPIC_API_KEY")):
            st.error("사이드바에 API 키를 입력해주세요.")
        else:
            client = get_client()
            img_bytes = img_file.read()
            img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
            media_type = img_file.type or "image/jpeg"

            st.image(img_bytes, caption="업로드된 이미지", use_column_width=True)

            with st.spinner("이미지 분석 중..."):
                try:
                    resp = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=1500,
                        system="당신은 자동차 부품 도면 및 품질 문서 전문 분석가입니다. 한국어로 상세히 답변하세요.",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                                {"type": "text", "text": question}
                            ]
                        }]
                    )
                    st.success("✅ 분석 완료!")
                    st.markdown(resp.content[0].text)
                except Exception as e:
                    st.error(f"오류: {e}")

# ───────────────────────────────────────────
# 푸터
# ───────────────────────────────────────────
st.markdown("---")
st.caption("재진님 전용 AI 비서 · Claude claude-sonnet-4-5 기반 · Powered by Anthropic")
