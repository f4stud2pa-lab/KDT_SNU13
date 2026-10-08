"""
그림과 감정을 기반으로 한 이야기 생성기 (Streamlit 웹 애플리케이션)
실행 방법:
    streamlit run app.py
"""

import os
from pathlib import Path
import streamlit as st

# story_engine 가져오기
from story_engine import StoryEngine, SENTIMENT_PROFILES, StoryResult

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(
    page_title="그림 & 감정 스토리텔러",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS 스타일링
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .story-card {
        background-color: #F8FAFC;
        border-left: 5px solid #3B82F6;
        padding: 20px 24px;
        border-radius: 8px;
        margin-top: 15px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .story-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 12px;
    }
    .story-body {
        font-size: 1.08rem;
        line-height: 1.8;
        color: #334155;
        white-space: pre-wrap;
    }
    .moral-box {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 12px 16px;
        border-radius: 6px;
        color: #92400E;
        font-weight: 500;
        margin-top: 15px;
    }
    .analysis-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }
    .badge {
        display: inline-block;
        padding: 3px 8px;
        font-size: 0.8rem;
        font-weight: 600;
        border-radius: 4px;
        background-color: #E0E7FF;
        color: #3730A3;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)



# 사이드바 설정 (API 키, 감정 설정, 모드 선택)
with st.sidebar:
    st.header("⚙️ 환경 설정")
    env_api_key = os.environ.get("OPENAI_API_KEY", "")
    api_key_input = st.text_input(
        "OpenAI API Key",
        value=env_api_key,
        type="password",
        help=".env 파일 또는 환경변수에 등록되어 있으면 자동 입력됩니다."
    )

    mock_mode = st.checkbox(
        "🧪 테스트 모드 (Mock Mode)",
        value=not bool(api_key_input),
        help="API 키 없이도 예시 4컷 강아지 스토리로 동작을 시연해볼 수 있습니다."
    )

    if mock_mode:
        st.info("ℹ️ 현재 Mock 모드입니다. 실제 API 비용 없이 빠르고 안전하게 동작을 테스트할 수 있습니다.")

    st.markdown("---")
    st.header("🎭 감정(Sentiment) 선택")

    sentiment_list = list(SENTIMENT_PROFILES.keys()) + ["직접 입력 (Custom)"]
    selected_option = st.radio("이야기에 담을 핵심 감정:", sentiment_list, index=0)

    if selected_option == "직접 입력 (Custom)":
        custom_sentiment = st.text_input("원하는 감정을 자유롭게 입력하세요:", placeholder="예: 아늑함, 신비로움, 비장함")
        target_sentiment = custom_sentiment.strip() if custom_sentiment.strip() else "행복"
        tone_preview = f"'{target_sentiment}'의 고유한 감정선과 분위기 반영"
        guide_preview = f"장면마다 '{target_sentiment}'의 느낌을 살려 서사를 전개합니다."
    else:
        target_sentiment = selected_option
        profile = SENTIMENT_PROFILES[target_sentiment]
        tone_preview = profile["tone"]
        guide_preview = profile["story_guide"]

    with st.expander("🔍 선택된 감정의 스토리 템플릿 & 어조", expanded=True):
        st.markdown(f"**어조(Tone):** {tone_preview}")
        st.markdown(f"**스토리 지침:** {guide_preview}")


# 메인 헤더
st.markdown('<div class="main-title"> 그림 & 감정 기반 이야기 생성기</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">'
    '여러 장의 그림을 순서대로 업로드하고 원하는 감정을 선택하면, '
    '그림 속 요소를 정밀 분석하여 하나의 감동적인 이야기로 엮어냅니다.'
    '</div>',
    unsafe_allow_html=True
)

# 입력 영역: 그림 업로드
st.subheader("1. 그림(이미지) 업로드")
uploaded_files = st.file_uploader(
    "이야기로 연결할 그림들을 순서대로 선택하세요 (다중 선택 가능):",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
    help="파일 선택 창에서 여러 장의 이미지를 한 번에 선택할 수 있습니다."
)

if uploaded_files:
    st.markdown(f"**총 {len(uploaded_files)}개의 그림이 등록되었습니다.** (순서대로 이야기가 전개됩니다)")

    cols = st.columns(min(len(uploaded_files), 4))
    for idx, uploaded_file in enumerate(uploaded_files):
        with cols[idx % 4]:
            st.image(uploaded_file, caption=f"[그림 {idx + 1}] {uploaded_file.name}", use_container_width=True)
else:
    st.info("💡 그림 파일을 2장 이상 업로드해 보세요! 예제 이미지가 없다면 터미널에서 `python create_sample_images.py`를 실행해 샘플 4컷 이미지를 생성할 수 있습니다.")

st.markdown("---")


# 생성 버튼 및 처리
st.subheader("2. 감성 이야기 생성")

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    generate_btn = st.button("✨ 이야기 생성하기", type="primary", use_container_width=True)

if generate_btn:
    if not uploaded_files:
        st.warning("⚠️ 이야기로 엮을 그림을 1장 이상 업로드해 주세요.")
    else:
        # API 키 검증
        active_api_key = api_key_input.strip()
        if not active_api_key and not mock_mode:
            st.error("❌ OpenAI API 키를 입력하거나, 좌측 사이드바에서 [테스트 모드(Mock Mode)]를 체크해 주세요.")
        else:
            with st.spinner(f"'{target_sentiment}' 감정의 톤으로 그림들을 분석하고 이야기를 창작 중입니다..."):
                try:
                    # 이미지 바이트 리스트 및 MIME 타입 추출
                    image_bytes_list = []
                    mime_types = []
                    for f in uploaded_files:
                        image_bytes_list.append(f.getvalue())
                        mime_types.append(f.type or "image/jpeg")

                    # 엔진 구동
                    engine = StoryEngine(
                        api_key=active_api_key if not mock_mode else "mock-key",
                        mock_mode=mock_mode
                    )
                    result: StoryResult = engine.generate_story(
                        images=image_bytes_list,
                        sentiment=target_sentiment,
                        image_mime_types=mime_types
                    )

                    st.session_state["last_result"] = result
                    st.success("🎉 이야기가 성공적으로 완성되었습니다!")

                except Exception as e:
                    st.error(f"이야기 생성 중 오류가 발생했습니다: {str(e)}")


# 결과 출력 탭
if "last_result" in st.session_state:
    res: StoryResult = st.session_state["last_result"]

    tab1, tab2, tab3 = st.tabs(["📖 완성된 이야기", "🔍 그림별 AI 분석 리포트", "🎭 감정 및 어조 설정"])

    with tab1:
        st.markdown(f"""
        <div class="story-card">
            <div class="story-title">📖 {res.title}</div>
            <div style="margin-bottom: 12px;">
                <span class="badge">감정: {res.sentiment}</span>
                <span class="badge" style="background-color: #FEF3C7; color: #92400E;">분위기: {res.sentiment_profile.get('tone', '')}</span>
            </div>
            <div class="story-body">{res.story}</div>
        </div>
        """, unsafe_allow_html=True)

        if res.moral_or_thought:
            st.markdown(f'<div class="moral-box">💡 <strong>한 줄 여운:</strong> {res.moral_or_thought}</div>', unsafe_allow_html=True)

        # 텍스트 다운로드 버튼
        full_text = f"제목: {res.title}\n감정: {res.sentiment}\n\n[스토리 전문]\n{res.story}\n\n[한 줄 여운]\n{res.moral_or_thought or ''}\n\n"
        full_text += "[각 그림별 분석]\n"
        for a in res.image_analyses:
            full_text += f"- 그림 {a.index}: {a.summary}\n  인물: {a.characters}\n  배경: {a.background}\n  사건: {a.action_or_event}\n"

        st.download_button(
            label="📥 이야기 텍스트 파일(.txt) 다운로드",
            data=full_text,
            file_name=f"story_{res.sentiment}.txt",
            mime="text/plain"
        )

    with tab2:
        st.markdown("### 그림별 정밀 분석 (OpenAI Vision)")
        st.caption("각 그림의 등장인물, 배경 장소, 행동 및 시각적 특징을 분석한 결과입니다.")

        for a in res.image_analyses:
            with st.container():
                st.markdown(f"""
                <div class="analysis-card">
                    <h4 style="margin: 0 0 8px 0; color: #1E293B;">그림 {a.index}: {a.summary}</h4>
                    <p style="margin: 4px 0;"><strong>등장 인물/주체:</strong> {a.characters}</p>
                    <p style="margin: 4px 0;"><strong>배경 및 장소:</strong> {a.background}</p>
                    <p style="margin: 4px 0;"><strong>행동 및 상황:</strong> {a.action_or_event}</p>
                    {f'<p style="margin: 4px 0; color: #64748B;"><strong>특징:</strong> {", ".join(a.key_details)}</p>' if a.key_details else ''}
                </div>
                """, unsafe_allow_html=True)

    with tab3:
        st.markdown("### 🎭 적용된 감정 템플릿 및 어조 가이드")
        st.write(f"- **선택 감정:** {res.sentiment}")
        st.write(f"- **적용 어조(Tone):** {res.sentiment_profile.get('tone', '')}")
        st.write(f"- **스토리 전개 지침:** {res.sentiment_profile.get('story_guide', '')}")
        if "example_expressions" in res.sentiment_profile:
            st.write(f"- **추천 감성 표현들:** {', '.join(res.sentiment_profile['example_expressions'])}")
