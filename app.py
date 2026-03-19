import streamlit as st
import google.generativeai as genai
import base64
import json
from datetime import datetime

# ───────────────────────────────────────────
# 페이지 설정
# ───────────────────────────────────────────
st.set_page_config(
    page_title="CTR 품질팀 AI 비서",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    .stButton > button {
        background: #2d6a9f;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
    }
    .stButton > button:hover { background: #1e5a8f; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
  <h1>🤖 CTR 품질팀 AI 비서</h1>
  <p>영어 메일 · PDF · 도면 분석 · Tesla 회의 대응 가이드</p>
</div>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────
# 사이드바
# ───────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    api_key = st.text_input(
        "Gemini API 키",
        type="password",
        placeholder="AIzaSy...",
        help="Google AI Studio에서 발급받은 무료 API 키"
    )
    st.markdown("---")
    mode = st.radio(
        "**기능 선택**",
        ["📄 문서·메일 요약", "🎤 회의 코치", "🖼️ 도면·이미지 분석"],
    )
    st.markdown("---")
    st.markdown("🔑 키 발급: [aistudio.google.com](https://aistudio.google.com)")
    st.markdown("✅ **무료 등급** 사용 중")

# ───────────────────────────────────────────
# Gemini 클라이언트
# ───────────────────────────────────────────
def get_model(vision=False):
    key = api_key or st.secrets.get("GEMINI_API_KEY", "")
    if not key:
        return None
    genai.configure(api_key=key)
    model_name = "gemini-2.5-flash"
    return genai.GenerativeModel(model_name)

def need_key():
    st.error("왼쪽 사이드바에 Gemini API 키를 입력해주세요.")

# ───────────────────────────────────────────
# 모드 1 — 문서·메일 요약
# ───────────────────────────────────────────
if "📄 문서·메일 요약" in mode:
    st.subheader("📄 문서·메일 요약기")
    st.caption("이메일이나 문서 내용을 붙여넣으면 핵심만 정리해드려요")

    tab1, tab2 = st.tabs(["📋 텍스트 붙여넣기", "📁 PDF 업로드"])

    content = None

    with tab1:
        raw_text = st.text_area(
            "이메일 또는 문서 내용",
            height=250,
            placeholder="예) Dear Jaejin, Please find attached the updated SIE requirements for SEMI Tie Rod...",
        )
        if raw_text.strip():
            content = ("text", raw_text.strip())

    with tab2:
        uploaded = st.file_uploader("PDF 파일 선택", type=["pdf"])
        if uploaded:
            pdf_bytes = uploaded.read()
            pdf_b64 = base64.standard_b64encode(pdf_bytes).decode()
            content = ("pdf", pdf_b64, uploaded.name)
            st.success(f"✅ {uploaded.name} 업로드 완료")

    context = st.text_area(
        "📌 추가 배경 설명 (선택)",
        height=70,
        placeholder="예) Tesla SEMI Tie Rod 1차 공급업체 심사 관련 메일입니다.",
    )

    col1, col2 = st.columns([3,1])
    with col1:
        lang = st.selectbox("출력 언어", ["한국어", "한국어 + 영어 병기"])
    with col2:
        run = st.button("🚀 분석 시작")

    if run:
        if not content:
            st.warning("텍스트를 입력하거나 PDF를 업로드해주세요.")
        elif not (api_key or st.secrets.get("GEMINI_API_KEY")):
            need_key()
        else:
            model = get_model()
            bilingual = "병기" in lang

            if content[0] == "text":
                doc_text = content[1]
            else:
                doc_text = f"[PDF 파일: {content[2]}] — 아래 base64 인코딩된 PDF를 분석해주세요."

            prompt = f"""당신은 CTR(자동차 부품 제조사) 선행개발품질팀 전문 분석 비서입니다.
APQP, SIE, PPAP, 8D 등 자동차 품질 용어에 능통합니다.

다음 문서를 분석하고 반드시 아래 JSON 형식으로만 답하세요. 다른 말 하지 마세요.
{{
  "title": "문서 주제 (20자 이내)",
  "summary": "전체 내용 3-5문장 요약",
  "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
  "action_items": ["조치 필요 항목 1", "조치 필요 항목 2"],
  "urgency": "높음 또는 보통 또는 낮음",
  "suggested_reply": "추천 영어 답변 (3-4문장)",
  "suggested_reply_kr": "위 답변의 한국어 해석"
}}

{'모든 항목을 한국어와 영어로 병기하세요.' if bilingual else '한국어로 작성하세요.'}
추가 배경: {context if context else '없음'}

분석할 문서:
{doc_text}"""

            with st.spinner("🔍 AI 분석 중..."):
                try:
                    response = model.generate_content(prompt)
                    raw = response.text.strip().replace("```json","").replace("```","").strip()
                    r = json.loads(raw)

                    st.success("✅ 분석 완료!")
                    urg = {"높음":"🔴","보통":"🟡","낮음":"🟢"}.get(r.get("urgency","보통"),"🟡")
                    st.markdown(f"## {r.get('title','')}  {urg} 긴급도: {r.get('urgency','보통')}")

                    st.markdown("### 📝 요약")
                    st.info(r.get("summary",""))

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("### 💡 핵심 포인트")
                        for p in r.get("key_points",[]):
                            st.markdown(f"- {p}")
                    with c2:
                        st.markdown("### ✅ 조치 필요 항목")
                        for a in r.get("action_items",[]):
                            st.markdown(f"- {a}")

                    st.markdown("### ✉️ 추천 영어 답변")
                    st.code(r.get("suggested_reply",""), language=None)
                    st.caption(f"🇰🇷 해석: {r.get('suggested_reply_kr','')}")

                    report = f"""[CTR 품질팀 AI 분석] {datetime.now().strftime('%Y-%m-%d %H:%M')}
제목: {r.get('title','')}  |  긴급도: {r.get('urgency','')}

[요약]
{r.get('summary','')}

[핵심 포인트]
{chr(10).join('- '+p for p in r.get('key_points',[]))}

[조치 항목]
{chr(10).join('- '+a for a in r.get('action_items',[]))}

[추천 영어 답변]
{r.get('suggested_reply','')}

[한국어 해석]
{r.get('suggested_reply_kr','')}
"""
                    st.download_button("📥 결과 저장 (.txt)", report,
                        file_name=f"CTR_분석_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")

                except json.JSONDecodeError:
                    st.warning("구조화 실패 — 원문 표시")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"오류: {e}")

# ───────────────────────────────────────────
# 모드 2 — 회의 코치
# ───────────────────────────────────────────
elif "🎤 회의 코치" in mode:
    st.subheader("🎤 Tesla·고객사 회의 코치")
    st.caption("회의 중 들은 내용을 붙여넣으면 번역·분석·답변 3가지를 드려요")

    transcript = st.text_area(
        "회의 내용 (영어 또는 한국어)",
        height=250,
        placeholder='예) Customer: "The durability test results are inconsistent. We suspect a material defect from your side."',
    )
    context2 = st.text_area("📌 회의 배경 (선택)", height=70,
        placeholder="예) Tesla SEMI Tie Rod 내구성 시험 결과 검토 회의 / 1차 공급업체 감사")

    if st.button("🎯 회의 분석 시작"):
        if not transcript.strip():
            st.warning("회의 내용을 입력해주세요.")
        elif not (api_key or st.secrets.get("GEMINI_API_KEY")):
            need_key()
        else:
            model = get_model()
            prompt = f"""당신은 CTR 자동차 품질팀 회의 전문 코치입니다.
APQP, SIE, 8D, PPAP 등 자동차 품질 프로세스에 정통합니다.

아래 회의 내용을 분석하고 반드시 JSON만 반환하세요:
{{
  "situation": "현재 상황 요약 (2-3문장)",
  "customer_concern": "고객의 핵심 우려사항",
  "our_position": "CTR 측 권장 대응 방향",
  "reply_options": [
    {{"label": "신중한 답변 (사실 확인 후 대응)", "english": "...", "korean": "..."}},
    {{"label": "적극적 답변 (즉각 대응)", "english": "...", "korean": "..."}},
    {{"label": "시간 확보 답변 (내부 검토 요청)", "english": "...", "korean": "..."}}
  ],
  "caution": "주의사항 또는 절대 하지 말아야 할 표현",
  "quality_terms": ["관련 품질 용어 1", "관련 품질 용어 2"]
}}

배경: {context2 if context2 else '없음'}
회의 내용:
{transcript}"""

            with st.spinner("분석 중..."):
                try:
                    resp = model.generate_content(prompt)
                    raw = resp.text.strip().replace("```json","").replace("```","").strip()
                    r = json.loads(raw)

                    st.success("✅ 분석 완료!")
                    st.info(f"**📊 상황:** {r.get('situation','')}")
                    st.warning(f"**⚠️ 고객 우려:** {r.get('customer_concern','')}")
                    st.success(f"**🎯 대응 방향:** {r.get('our_position','')}")

                    if r.get("quality_terms"):
                        st.markdown("**🔖 관련 품질 용어:** " + " · ".join(r.get("quality_terms",[])))

                    st.markdown("---")
                    st.markdown("### 💬 추천 답변 3가지")
                    for opt in r.get("reply_options",[]):
                        with st.expander(f"✉️ {opt.get('label','')}"):
                            st.code(opt.get("english",""), language=None)
                            st.caption(f"🇰🇷 {opt.get('korean','')}")

                    if r.get("caution"):
                        st.error(f"🚫 주의: {r.get('caution')}")

                except Exception as e:
                    st.error(f"오류: {e}")

# ───────────────────────────────────────────
# 모드 3 — 도면·이미지 분석
# ───────────────────────────────────────────
else:
    st.subheader("🖼️ 도면·이미지 분석")
    st.caption("도면 캡처, 사진, 스크린샷을 올리면 기술 내용을 분석해드려요")

    img_file = st.file_uploader("이미지 업로드 (JPG, PNG)", type=["jpg","jpeg","png","webp"])
    question = st.text_area(
        "❓ 이 이미지에 대해 무엇이 궁금하신가요?",
        height=100,
        placeholder="예) 이 도면에서 Tie Rod 연결부 규격과 공차를 확인해주세요.",
    )

    if st.button("🔍 이미지 분석"):
        if not img_file:
            st.warning("이미지를 업로드해주세요.")
        elif not question.strip():
            st.warning("질문을 입력해주세요.")
        elif not (api_key or st.secrets.get("GEMINI_API_KEY")):
            need_key()
        else:
            img_bytes = img_file.read()
            st.image(img_bytes, caption="업로드된 이미지", use_column_width=True)

            model = get_model(vision=True)
            import PIL.Image, io
            pil_img = PIL.Image.open(io.BytesIO(img_bytes))

            with st.spinner("이미지 분석 중..."):
                try:
                    resp = model.generate_content([
                        "당신은 CTR 자동차 부품 도면 및 품질 문서 전문 분석가입니다. 한국어로 상세히 답변하세요.\n\n질문: " + question,
                        pil_img
                    ])
                    st.success("✅ 분석 완료!")
                    st.markdown(resp.text)
                except Exception as e:
                    st.error(f"오류: {e}")

# ───────────────────────────────────────────
# 푸터
# ───────────────────────────────────────────
st.markdown("---")
st.caption("CTR 선행개발품질팀 AI 비서 · Gemini 1.5 Flash 기반 · 무료 운영")
