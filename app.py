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
        ["📄 문서·메일 요약", "🎤 회의 코치", "📂 파일 종합 분석"],
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
    model_name = "models/gemini-1.5-flash"
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
  "suggested_reply_sentences": [
    {{"en": "영어 문장 1", "kr": "한국어 해석 1"}},
    {{"en": "영어 문장 2", "kr": "한국어 해석 2"}},
    {{"en": "영어 문장 3", "kr": "한국어 해석 3"}},
    {{"en": "영어 문장 4", "kr": "한국어 해석 4"}}
  ]
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
                    sentences = r.get("suggested_reply_sentences", [])
                    if sentences:
                        full_en = " ".join([s.get("en","") for s in sentences])
                        st.markdown(f"""
<div style='background:#e8f4fd;border:2px solid #2d6a9f;border-radius:14px;padding:24px 28px;margin:8px 0 20px 0'>
  <div style='font-size:0.8rem;color:#2d6a9f;font-weight:700;margin-bottom:12px;letter-spacing:0.05em'>📋 전체 복사용 (영어)</div>
  <div style='font-size:1.15rem;color:#1e3a5f;line-height:2.0;font-weight:500'>{full_en}</div>
</div>""", unsafe_allow_html=True)
                        for i, s in enumerate(sentences, 1):
                            en = s.get("en","")
                            kr = s.get("kr","")
                            is_key = i == 1
                            bg = "#fff8e1" if is_key else "#f8fbff"
                            border = "#e65100" if is_key else "#2d6a9f"
                            en_weight = "800" if is_key else "600"
                            if is_key:
                                badge_html = "<span style='background:#e65100;color:white;border-radius:12px;padding:3px 12px;font-size:0.78rem;font-weight:700;margin-right:8px'>🔑 핵심문장</span>"
                            else:
                                badge_html = f"<span style='background:#e8f0fe;color:#2d6a9f;border-radius:12px;padding:3px 12px;font-size:0.78rem;font-weight:600;margin-right:8px'>문장 {i}</span>"
                            st.markdown(f"""
<div style='background:{bg};border-left:6px solid {border};border-radius:0 12px 12px 0;padding:24px 28px;margin:14px 0;'>
  <div style='margin-bottom:12px'>{badge_html}</div>
  <div style='font-size:1.3rem;color:#1e3a5f;font-weight:{en_weight};line-height:2.0;margin-bottom:16px'>🇺🇸 {en}</div>
  <div style='height:1px;background:#dde6f0;margin-bottom:16px'></div>
  <div style='font-size:1.18rem;color:#333;line-height:2.0;font-weight:500'>🇰🇷 {kr}</div>
</div>""", unsafe_allow_html=True)

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
    st.caption("Teams 자막이나 회의 내용을 붙여넣으면 즉시 번역·분석·답변 3가지를 드려요")

    st.info("💡 **사용 팁**: Teams 회의 중 → 상단 '...' → '실시간 자막' 켜기 → 자막 복사 → 여기 붙여넣기!")

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
  "translation": "회의 내용 전체 한국어 번역 (영어인 경우만)",
  "situation": "현재 상황 요약 (2-3문장)",
  "customer_concern": "고객의 핵심 우려사항",
  "our_position": "CTR 측 권장 대응 방향",
  "reply_options": [
    {{
      "label": "신중한 답변 (사실 확인 후 대응)",
      "sentences": [
        {{"en": "영어 문장1", "kr": "한국어 해석1"}},
        {{"en": "영어 문장2", "kr": "한국어 해석2"}},
        {{"en": "영어 문장3", "kr": "한국어 해석3"}}
      ]
    }},
    {{
      "label": "적극적 답변 (즉각 대응)",
      "sentences": [
        {{"en": "영어 문장1", "kr": "한국어 해석1"}},
        {{"en": "영어 문장2", "kr": "한국어 해석2"}},
        {{"en": "영어 문장3", "kr": "한국어 해석3"}}
      ]
    }},
    {{
      "label": "시간 확보 답변 (내부 검토 요청)",
      "sentences": [
        {{"en": "영어 문장1", "kr": "한국어 해석1"}},
        {{"en": "영어 문장2", "kr": "한국어 해석2"}},
        {{"en": "영어 문장3", "kr": "한국어 해석3"}}
      ]
    }}
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

                    # 자동 회의록
                    if r.get("translation"):
                        st.markdown("### 📋 자동 회의록 (영어 & 한국어)")
                        col_en, col_kr = st.columns(2)
                        with col_en:
                            st.markdown("**🇺🇸 원문 영어**")
                            st.markdown(f"<div style='background:#f0f7ff;border-radius:10px;padding:16px;font-size:1rem;line-height:1.8;min-height:120px'>{transcript}</div>", unsafe_allow_html=True)
                        with col_kr:
                            st.markdown("**🇰🇷 한국어 번역**")
                            st.markdown(f"<div style='background:#fff8e1;border-radius:10px;padding:16px;font-size:1rem;line-height:1.8;min-height:120px'>{r.get('translation','')}</div>", unsafe_allow_html=True)
                        st.markdown("---")

                    # 상황 분석
                    st.markdown("### 🔍 상황 분석")
                    st.markdown(f"<div style='background:#e3f2fd;border-left:5px solid #1976d2;border-radius:0 10px 10px 0;padding:14px 18px;font-size:1.05rem;font-weight:600;margin:6px 0'>📊 {r.get('situation','')}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='background:#fff3e0;border-left:5px solid #e65100;border-radius:0 10px 10px 0;padding:14px 18px;font-size:1.05rem;font-weight:700;margin:6px 0'>⚠️ 고객 핵심 우려: {r.get('customer_concern','')}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='background:#e8f5e9;border-left:5px solid #2e7d32;border-radius:0 10px 10px 0;padding:14px 18px;font-size:1.05rem;font-weight:600;margin:6px 0'>🎯 CTR 대응 방향: {r.get('our_position','')}</div>", unsafe_allow_html=True)

                    if r.get("quality_terms"):
                        st.markdown("**🔖 관련 품질 용어:** " + " · ".join(r.get("quality_terms",[])))

                    # 추천 답변 3가지
                    st.markdown("---")
                    st.markdown("### 💬 추천 답변 3가지")
                    for opt in r.get("reply_options",[]):
                        with st.expander(f"✉️ {opt.get('label','')}"):
                            sents = opt.get("sentences", [])
                            if sents:
                                full = " ".join([s.get("en","") for s in sents])
                                st.markdown(f"<div style='background:#e8f4fd;border:2px solid #2d6a9f;border-radius:10px;padding:16px 20px;margin-bottom:12px'><div style='font-size:0.8rem;color:#2d6a9f;font-weight:700;margin-bottom:8px'>📋 전체 복사용</div><div style='font-size:1.05rem;color:#1e3a5f;line-height:1.8'>{full}</div></div>", unsafe_allow_html=True)
                                for i, s in enumerate(sents, 1):
                                    en = s.get("en","")
                                    kr = s.get("kr","")
                                    st.markdown(f"<div style='background:#f8fbff;border-left:4px solid #2d6a9f;border-radius:0 8px 8px 0;padding:14px 18px;margin:8px 0'><div style='font-size:1.1rem;color:#1e3a5f;font-weight:700;line-height:1.8'>🇺🇸 {en}</div><div style='font-size:1rem;color:#444;margin-top:8px;line-height:1.8;border-top:1px dashed #ccc;padding-top:8px'>🇰🇷 {kr}</div></div>", unsafe_allow_html=True)
                            else:
                                st.code(opt.get("english",""), language=None)
                                st.caption(f"🇰🇷 {opt.get('korean','')}")

                    if r.get("caution"):
                        st.error(f"🚫 주의: {r.get('caution')}")

                except Exception as e:
                    st.error(f"오류: {e}")

# ───────────────────────────────────────────
# 모드 3 — 파일 분석 (PDF / 엑셀 / 도면·이미지)
# ───────────────────────────────────────────
else:
    st.subheader("📂 파일 종합 분석")
    st.caption("PDF · 엑셀 · 도면 이미지를 올리면 내용 정리 + 요청사항 + 답변안을 드려요")

    file_tab1, file_tab2, file_tab3 = st.tabs(["📄 PDF 분석", "📊 엑셀 분석", "🖼️ 도면·이미지 분석"])

    # ── PDF 탭 ──────────────────────────────
    with file_tab1:
        st.markdown("**PDF 파일을 올리면 내용 요약 + 요청사항 + 영어 답변안을 드려요**")
        pdf_file = st.file_uploader("PDF 업로드", type=["pdf"], key="pdf3")
        pdf_question = st.text_area("❓ 이 PDF에서 특별히 확인하고 싶은 것 (선택)",
            height=80, placeholder="예) 요구되는 시험 항목과 제출 기한을 정리해주세요.",
            key="pdfq3")
        pdf_ctx = st.text_area("📌 배경 설명 (선택)", height=60,
            placeholder="예) Tesla SEMI Tie Rod SIE 요구사항 문서입니다.", key="pdfctx3")

        if st.button("🔍 PDF 분석", key="pdfbtn3"):
            if not pdf_file:
                st.warning("PDF를 업로드해주세요.")
            elif not (api_key or st.secrets.get("GEMINI_API_KEY")):
                need_key()
            else:
                pdf_bytes = pdf_file.read()
                pdf_b64 = base64.standard_b64encode(pdf_bytes).decode()
                model = get_model()
                prompt = f"""당신은 CTR 자동차 품질팀 전문 분석가입니다.
첨부된 PDF를 분석하고 반드시 JSON만 반환하세요:
{{
  "title": "문서 제목 또는 주제",
  "overview": "문서 전체 개요 (3-5문장)",
  "main_contents": [
    {{"section": "섹션명", "content": "내용 요약", "important": true/false}}
  ],
  "requirements": ["요구사항 1", "요구사항 2"],
  "deadlines": ["기한/일정 1", "기한/일정 2"],
  "action_items": ["CTR이 해야 할 조치 1", "조치 2"],
  "reply_sentences": [
    {{"en": "영어 답변 문장1", "kr": "한국어 해석1"}},
    {{"en": "영어 답변 문장2", "kr": "한국어 해석2"}},
    {{"en": "영어 답변 문장3", "kr": "한국어 해석3"}}
  ]
}}
추가 질문: {pdf_question if pdf_question else '없음'}
배경: {pdf_ctx if pdf_ctx else '없음'}"""

                with st.spinner("📄 PDF 분석 중..."):
                    try:
                        import google.generativeai as genai2
                        key2 = api_key or st.secrets.get("GEMINI_API_KEY","")
                        genai2.configure(api_key=key2)
                        m2 = genai2.GenerativeModel("gemini-2.5-flash")
                        resp = m2.generate_content([
                            {"mime_type": "application/pdf", "data": pdf_b64},
                            prompt
                        ])
                        raw = resp.text.strip().replace("```json","").replace("```","").strip()
                        r = json.loads(raw)

                        st.success("✅ PDF 분석 완료!")
                        st.markdown(f"## 📄 {r.get('title','')}")
                        st.markdown(f"<div style='background:#e8f4fd;border-left:5px solid #2d6a9f;border-radius:0 10px 10px 0;padding:16px 20px;font-size:1.05rem;line-height:1.8'>{r.get('overview','')}</div>", unsafe_allow_html=True)

                        st.markdown("---")
                        st.markdown("### 📑 주요 내용")
                        for sec in r.get("main_contents", []):
                            is_imp = sec.get("important", False)
                            bg = "#fff8e1" if is_imp else "#f8f9fa"
                            border = "#e65100" if is_imp else "#90caf9"
                            badge = " 🔴 중요" if is_imp else ""
                            st.markdown(f"<div style='background:{bg};border-left:5px solid {border};border-radius:0 8px 8px 0;padding:14px 18px;margin:8px 0'><div style='font-size:1rem;font-weight:700;color:#1e3a5f'>{sec.get('section','')}{badge}</div><div style='font-size:0.98rem;color:#333;margin-top:6px;line-height:1.7'>{sec.get('content','')}</div></div>", unsafe_allow_html=True)

                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("### ✅ 요구사항")
                            for req in r.get("requirements", []):
                                st.markdown(f"- **{req}**")
                            st.markdown("### 📅 기한·일정")
                            for dl in r.get("deadlines", []):
                                st.markdown(f"- 🗓️ {dl}")
                        with c2:
                            st.markdown("### 🎯 CTR 조치 항목")
                            for ai in r.get("action_items", []):
                                st.markdown(f"- ✔️ {ai}")

                        st.markdown("---")
                        st.markdown("### ✉️ 추천 영어 답변")
                        sents = r.get("reply_sentences", [])
                        if sents:
                            full = " ".join([s.get("en","") for s in sents])
                            st.markdown(f"<div style='background:#e8f4fd;border:2px solid #2d6a9f;border-radius:12px;padding:18px 22px;margin-bottom:12px'><div style='font-size:0.8rem;color:#2d6a9f;font-weight:700;margin-bottom:8px'>📋 전체 복사용</div><div style='font-size:1.05rem;color:#1e3a5f;line-height:1.8'>{full}</div></div>", unsafe_allow_html=True)
                            for s in sents:
                                st.markdown(f"<div style='background:#f8fbff;border-left:4px solid #2d6a9f;border-radius:0 8px 8px 0;padding:14px 18px;margin:8px 0'><div style='font-size:1.1rem;color:#1e3a5f;font-weight:700;line-height:1.8'>🇺🇸 {s.get('en','')}</div><div style='font-size:1rem;color:#444;margin-top:8px;line-height:1.8;border-top:1px dashed #ccc;padding-top:8px'>🇰🇷 {s.get('kr','')}</div></div>", unsafe_allow_html=True)

                    except json.JSONDecodeError:
                        st.warning("구조화 실패 — 원문 표시")
                        st.markdown(resp.text)
                    except Exception as e:
                        st.error(f"오류: {e}")

    # ── 엑셀 탭 ─────────────────────────────
    with file_tab2:
        st.markdown("**엑셀 파일을 올리면 데이터 내용 정리 + 이슈 + 요청사항을 분석해드려요**")
        xl_file = st.file_uploader("엑셀 업로드 (.xlsx, .xls, .csv)", type=["xlsx","xls","csv"], key="xl")
        xl_question = st.text_area("❓ 특별히 확인하고 싶은 것 (선택)",
            height=80, placeholder="예) 불량률이 높은 항목과 원인을 정리해주세요.",
            key="xlq")
        xl_ctx = st.text_area("📌 배경 설명 (선택)", height=60,
            placeholder="예) CTR P32R 내구시험 결과 데이터입니다.", key="xlctx")

        if st.button("📊 엑셀 분석", key="xlbtn"):
            if not xl_file:
                st.warning("엑셀 파일을 업로드해주세요.")
            elif not (api_key or st.secrets.get("GEMINI_API_KEY")):
                need_key()
            else:
                try:
                    import pandas as pd
                    import io as io2

                    # 파일 읽기
                    xl_bytes = xl_file.read()
                    if xl_file.name.endswith(".csv"):
                        df = pd.read_csv(io2.BytesIO(xl_bytes), encoding="utf-8-sig")
                    else:
                        df = pd.read_excel(io2.BytesIO(xl_bytes))

                    st.markdown(f"**📊 데이터 미리보기** ({len(df)}행 × {len(df.columns)}열)")
                    st.dataframe(df.head(20), use_container_width=True)

                    # 텍스트 변환
                    data_text = df.to_string(max_rows=100, max_cols=20)
                    cols = list(df.columns)

                    model = get_model()
                    prompt = f"""당신은 CTR 자동차 품질팀 데이터 분석 전문가입니다.
아래 엑셀 데이터를 분석하고 반드시 JSON만 반환하세요:
{{
  "title": "데이터 주제 요약",
  "overview": "데이터 전체 개요 (3-4문장)",
  "columns_desc": "주요 열(컬럼) 설명",
  "key_findings": [
    {{"finding": "주요 발견사항", "important": true/false}}
  ],
  "issues": ["문제점 또는 이슈 1", "이슈 2"],
  "requirements": ["요청사항 또는 조치 필요 항목 1", "항목 2"],
  "recommendations": ["개선 권고사항 1", "권고사항 2"],
  "reply_sentences": [
    {{"en": "영어 답변 문장1", "kr": "한국어 해석1"}},
    {{"en": "영어 답변 문장2", "kr": "한국어 해석2"}},
    {{"en": "영어 답변 문장3", "kr": "한국어 해석3"}}
  ]
}}
열 목록: {cols}
추가 질문: {xl_question if xl_question else '없음'}
배경: {xl_ctx if xl_ctx else '없음'}

데이터:
{data_text[:3000]}"""

                    with st.spinner("📊 엑셀 데이터 분석 중..."):
                        resp = model.generate_content(prompt)
                        raw = resp.text.strip().replace("```json","").replace("```","").strip()
                        r = json.loads(raw)

                        st.success("✅ 엑셀 분석 완료!")
                        st.markdown(f"## 📊 {r.get('title','')}")
                        st.markdown(f"<div style='background:#e8f4fd;border-left:5px solid #2d6a9f;border-radius:0 10px 10px 0;padding:16px 20px;font-size:1.05rem;line-height:1.8'>{r.get('overview','')}</div>", unsafe_allow_html=True)
                        st.caption(f"📋 컬럼 설명: {r.get('columns_desc','')}")

                        st.markdown("### 🔍 주요 발견사항")
                        for f in r.get("key_findings", []):
                            is_imp = f.get("important", False)
                            bg = "#fff8e1" if is_imp else "#f8f9fa"
                            border = "#e65100" if is_imp else "#90caf9"
                            badge = " 🔴" if is_imp else ""
                            st.markdown(f"<div style='background:{bg};border-left:5px solid {border};border-radius:0 8px 8px 0;padding:12px 18px;margin:6px 0;font-size:1rem;font-weight:{'700' if is_imp else '400'}'>{badge} {f.get('finding','')}</div>", unsafe_allow_html=True)

                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("### ⚠️ 문제점·이슈")
                            for iss in r.get("issues", []):
                                st.markdown(f"- 🔴 {iss}")
                            st.markdown("### 💡 개선 권고사항")
                            for rec in r.get("recommendations", []):
                                st.markdown(f"- ✅ {rec}")
                        with c2:
                            st.markdown("### 📌 요청사항·조치항목")
                            for req in r.get("requirements", []):
                                st.markdown(f"- ✔️ **{req}**")

                        st.markdown("---")
                        st.markdown("### ✉️ 추천 영어 답변")
                        sents = r.get("reply_sentences", [])
                        if sents:
                            full = " ".join([s.get("en","") for s in sents])
                            st.markdown(f"<div style='background:#e8f4fd;border:2px solid #2d6a9f;border-radius:12px;padding:18px 22px;margin-bottom:12px'><div style='font-size:0.8rem;color:#2d6a9f;font-weight:700;margin-bottom:8px'>📋 전체 복사용</div><div style='font-size:1.05rem;color:#1e3a5f;line-height:1.8'>{full}</div></div>", unsafe_allow_html=True)
                            for s in sents:
                                st.markdown(f"<div style='background:#f8fbff;border-left:4px solid #2d6a9f;border-radius:0 8px 8px 0;padding:14px 18px;margin:8px 0'><div style='font-size:1.1rem;color:#1e3a5f;font-weight:700;line-height:1.8'>🇺🇸 {s.get('en','')}</div><div style='font-size:1rem;color:#444;margin-top:8px;line-height:1.8;border-top:1px dashed #ccc;padding-top:8px'>🇰🇷 {s.get('kr','')}</div></div>", unsafe_allow_html=True)

                except json.JSONDecodeError:
                    st.warning("구조화 실패 — 원문 표시")
                    st.markdown(resp.text)
                except Exception as e:
                    st.error(f"오류: {e}")

    # ── 도면·이미지 탭 ──────────────────────
    with file_tab3:
        st.markdown("**도면 캡처, 사진, 스크린샷을 올리면 기술 내용을 분석해드려요**")
        img_file = st.file_uploader("이미지 업로드 (JPG, PNG)", type=["jpg","jpeg","png","webp"], key="img3")
        question = st.text_area("❓ 이 이미지에 대해 무엇이 궁금하신가요?",
            height=100, placeholder="예) 이 도면에서 Tie Rod 연결부 규격과 공차를 확인해주세요.",
            key="imgq3")

        if st.button("🔍 이미지 분석", key="imgbtn3"):
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
