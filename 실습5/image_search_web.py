"""
AI 텍스트 쿼리 이미지 검색 및 스마트 이미지 분류기 (image_search_web.py)
=======================================================================
Streamlit 기반 인터랙티브 웹 애플리케이션
- 탭 1: 🔎 텍스트 쿼리로 이미지 검색 (Top 1 하이라이트 & Top 3 갤러리)
- 탭 2: 🏷️ 임의의 이미지 카테고리 자동 분류 (Zero-Shot Classification)
- 탭 3: 🖼️ 이미지-to-이미지 유사도 역검색 (Similar Image Search)
- 탭 4: ➕ 신규 이미지 보관함 등록 및 실시간 인덱싱 (Dynamic Ingestion)
"""

import os
import sys
import tempfile
from pathlib import Path

try:
    import streamlit as st
except ImportError:
    print("[오류] Streamlit이 설치되어 있지 않습니다. 'pip install streamlit'을 실행해주세요.")
    sys.exit(1)

from image_search_engine import (
    DEFAULT_CLASSIFICATION_CATEGORIES,
    ImageSearchEngine,
    SearchResult,
)


# -------------------------------------------------------------
# 페이지 설정
# -------------------------------------------------------------
st.set_page_config(
    page_title="AI 이미지 검색 & 스마트 분류 시스템",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# 커스텀 CSS 스타일링
# -------------------------------------------------------------
st.markdown("""
<style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.0rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .top1-badge {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        color: #000;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 12px;
        display: inline-block;
        font-size: 0.85rem;
    }
    .cat-badge {
        background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%);
        color: #FFF;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 12px;
        display: inline-block;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# 세션 상태 및 엔진 초기화
# -------------------------------------------------------------
if "engine" not in st.session_state:
    img_dir = Path("search_images")
    if not img_dir.exists() or not any(img_dir.iterdir()):
        from prepare_search_images import create_search_images
        create_search_images(str(img_dir))
    st.session_state.engine = ImageSearchEngine(image_dir="search_images")
    st.session_state.engine.build_index(verbose=False)


# -------------------------------------------------------------
# 사이드바: 설정 및 상태
# -------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시스템 설정 & 상태")

    engine: ImageSearchEngine = st.session_state.engine

    if engine.is_api_ready():
        st.success("🟢 OpenAI API 온라인 연동 중")
    else:
        st.info("🟡 로컬 시맨틱 시뮬레이션 모드 (API 키 미설정)")

    user_api_key = st.text_input(
        "OpenAI API Key (선택)",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help=".env에 설정되어 있거나 직접 입력할 수 있습니다."
    )

    if st.button("API Key 적용 및 엔진 재초기화", use_container_width=True):
        if user_api_key and not user_api_key.startswith("your_"):
            os.environ["OPENAI_API_KEY"] = user_api_key
            st.session_state.engine = ImageSearchEngine(image_dir="search_images", api_key=user_api_key)
            st.session_state.engine.build_index(force_refresh=True, verbose=False)
            st.success("새 API 키로 인덱스를 재구축했습니다!")
            st.rerun()

    st.markdown("---")
    st.subheader("📚 현재 등록된 이미지")
    items = engine.get_indexed_items_list()
    st.caption(f"총 {len(items)}개 이미지가 보관함에 등록되어 있습니다.")

    for it in items:
        with st.expander(f"🖼️ {it.title}"):
            if Path(it.file_path).exists():
                st.image(it.file_path, use_container_width=True)
            st.caption(f"**파일명:** `{it.filename}`")
            st.write(f"**설명:** {it.description}")

    st.markdown("---")
    if st.button("🔄 캐시 강제 새로고침 (Reindex)", use_container_width=True):
        with st.spinner("이미지 메타데이터 및 임베딩을 다시 빌드하는 중..."):
            st.session_state.engine.build_index(force_refresh=True, verbose=False)
            st.success("인덱스 갱신 완료!")
            st.rerun()


# -------------------------------------------------------------
# 메인 화면
# -------------------------------------------------------------
st.markdown('<div class="main-title">🔍 AI 이미지 검색 & 스마트 분류 시스템</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Vision API로 이미지의 시각적 요소를 파악하고, '
    'OpenAI 고차원 벡터 임베딩과 코사인 유사도로 텍스트 검색 및 임의의 이미지 자동 분류를 수행합니다.</div>',
    unsafe_allow_html=True
)

tab1, tab2, tab3, tab4 = st.tabs([
    "🔎 텍스트로 이미지 검색",
    "🏷️ 임의의 이미지 카테고리 분류",
    "🖼️ 유사 이미지 검색",
    "➕ 새 이미지 등록"
])


# =============================================================
# 탭 1: 텍스트로 이미지 검색
# =============================================================
with tab1:
    st.write("**추천 검색어 예시를 눌러보세요:**")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)

    selected_example = None
    if col_s1.button("🌅 자연 속 석양", use_container_width=True):
        selected_example = "자연 속 석양"
    if col_s2.button("🐕 공원에서 노는 강아지", use_container_width=True):
        selected_example = "공원에서 노는 귀여운 강아지"
    if col_s3.button("🌃 밤의 번화한 도시", use_container_width=True):
        selected_example = "밤의 번화한 도시 스카이라인"
    if col_s4.button("❄️ 눈 덮인 겨울 숲", use_container_width=True):
        selected_example = "눈 덮인 고요한 겨울 숲"

    query_input = st.text_input(
        "검색할 텍스트 쿼리를 입력하세요:",
        value=selected_example if selected_example else "",
        placeholder="예: '자연 속 석양', '귀여운 강아지', '도시 야경 불빛', '에메랄드빛 해변'...",
        key="main_query_input"
    )

    col_btn, col_k = st.columns([4, 1])
    with col_btn:
        search_clicked = st.button("🔎 검색 실행", type="primary", use_container_width=True, key="search_btn")
    with col_k:
        top_k_select = st.selectbox("출력 개수", options=[3, 5], index=0, key="top_k_box")

    if search_clicked or query_input:
        if not query_input.strip():
            st.warning("검색할 텍스트 쿼리를 입력해주세요.")
        else:
            with st.spinner("임베딩 분석 및 코사인 유사도 계산 중..."):
                results = engine.search(query_input.strip(), top_k=top_k_select)

            if results:
                top1 = results[0]

                st.markdown("---")
                st.markdown("### 🏆 최우선 추천 이미지 (1위 매칭)")

                c_img, c_info = st.columns([1, 1])
                with c_img:
                    if Path(top1.file_path).exists():
                        st.image(top1.file_path, caption=top1.title, use_container_width=True)
                with c_info:
                    st.markdown('<span class="top1-badge">⭐ 1등 매칭</span>', unsafe_allow_html=True)
                    st.markdown(f"### {top1.title}")
                    st.caption(f"📁 파일: `{top1.filename}`")
                    st.metric("코사인 유사도", f"{top1.similarity:.4f}", f"{top1.score_percent:.1f}% 일치")
                    st.progress(min(1.0, max(0.0, top1.score_percent / 100.0)))
                    st.markdown("**📝 이미지 상세 설명 (Vision API):**")
                    st.info(top1.description)

                st.markdown("---")
                st.markdown(f"### 📊 유사도 순위 Top {len(results)} 결과 비교")
                cols = st.columns(len(results))
                for i, res in enumerate(results):
                    with cols[i]:
                        st.markdown(f"#### #{res.rank}위 ({res.score_percent:.1f}%)")
                        if Path(res.file_path).exists():
                            st.image(res.file_path, use_container_width=True)
                        st.write(f"**{res.title}**")
                        st.caption(f"유사도: `{res.similarity:.4f}`")
                        st.progress(min(1.0, max(0.0, res.score_percent / 100.0)))
                        with st.expander("설명 보기"):
                            st.write(res.description)


# =============================================================
# 탭 2: 임의의 이미지 카테고리 자동 분류
# =============================================================
with tab2:
    st.subheader("🏷️ 임의의 이미지 카테고리 자동 분류 (Zero-Shot Classification)")
    st.markdown(
        "사용자가 업로드하거나 선택한 임의의 이미지를 **Vision API가 분석**하고, "
        "사전 정의된 카테고리들과의 **벡터 임베딩 코사인 유사도**를 비교하여 가장 알맞은 카테고리로 자동 분류합니다."
    )

    c_up1, c_up2 = st.columns([1, 1])
    with c_up1:
        uploaded_file = st.file_uploader(
            "새로운 임의의 이미지 파일 업로드 (.bmp, .png, .jpg, .jpeg, .webp)",
            type=["bmp", "png", "jpg", "jpeg", "webp"],
            key="classify_file_uploader"
        )
    with c_up2:
        st.write("**또는 기존 샘플 이미지 중에서 선택하여 테스트:**")
        sample_options = [it.filename for it in engine.get_indexed_items_list()]
        selected_sample = st.selectbox("샘플 이미지 선택", options=["선택 안 함"] + sample_options, key="classify_sample_select")

    target_classify_path = None
    temp_file_to_clean = None

    if uploaded_file is not None:
        # 임시 파일로 저장하여 분석
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix)
        tfile.write(uploaded_file.read())
        tfile.close()
        target_classify_path = Path(tfile.name)
        temp_file_to_clean = tfile.name
    elif selected_sample != "선택 안 함":
        target_classify_path = engine.image_dir / selected_sample

    if target_classify_path and target_classify_path.exists():
        st.markdown("---")
        c_prev, c_res = st.columns([1, 1.2])

        with c_prev:
            st.image(str(target_classify_path), caption="분류 대상 이미지", use_container_width=True)

        with c_res:
            with st.spinner("Vision API 시각 분석 및 카테고리 벡터 유사도 연산 중..."):
                c_result = engine.classify_image(target_classify_path)

            st.markdown(f'<span class="cat-badge">🎯 최적 카테고리</span>', unsafe_allow_html=True)
            st.markdown(f"### {c_result.predicted_category}")
            st.metric("분류 신뢰도 / 유사도", f"{c_result.similarity_score:.4f}", f"{c_result.confidence_percent:.1f}%")
            st.progress(min(1.0, max(0.0, c_result.confidence_percent / 100.0)))

            st.markdown("**📝 이미지 분석 내용:**")
            st.info(c_result.image_description)

            st.markdown("**💡 AI 판단 사유:**")
            st.success(c_result.reasoning)

        st.markdown("#### 📊 전체 카테고리별 유사도 순위")
        for rank, (cat_name, sim, pct) in enumerate(c_result.all_category_scores, 1):
            c1, c2, c3 = st.columns([3, 1, 3])
            c1.write(f"**#{rank} {cat_name}**")
            c2.write(f"`{sim:+.4f}` ({pct:4.1f}%)")
            c3.progress(min(1.0, max(0.0, pct / 100.0)))


# =============================================================
# 탭 3: 이미지-to-이미지 유사도 역검색
# =============================================================
with tab3:
    st.subheader("🖼️ 유사 이미지 검색 (Image-to-Image Search)")
    st.markdown("임의의 쿼리 이미지를 입력하면, 현재 보관함에 있는 이미지들 중 **가장 시각적/의미적으로 닮은 이미지**를 찾아냅니다.")

    query_img_file = st.file_uploader(
        "유사한 이미지를 찾을 쿼리 이미지 업로드",
        type=["bmp", "png", "jpg", "jpeg", "webp"],
        key="query_img_uploader"
    )

    if query_img_file is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=Path(query_img_file.name).suffix)
        tfile.write(query_img_file.read())
        tfile.close()

        c_q, c_sim_results = st.columns([1, 1.5])
        with c_q:
            st.image(tfile.name, caption="입력한 쿼리 이미지", use_container_width=True)

        with c_sim_results:
            with st.spinner("쿼리 이미지 분석 및 보관함 비교 중..."):
                sim_results = engine.search_by_image(tfile.name, top_k=3)

            st.markdown("### 🏆 가장 유사한 보관함 이미지")
            if sim_results:
                top_match = sim_results[0]
                st.write(f"**1위: {top_match.title}** (`{top_match.filename}`)")
                st.metric("유사도 점수", f"{top_match.similarity:.4f}", f"{top_match.score_percent:.1f}%")
                if Path(top_match.file_path).exists():
                    st.image(top_match.file_path, width=280)
                st.info(f"설명: {top_match.description}")

        st.markdown("---")
        st.markdown("### 📊 상위 유사 이미지 비교")
        cols = st.columns(len(sim_results))
        for i, res in enumerate(sim_results):
            with cols[i]:
                st.markdown(f"#### #{res.rank}위 ({res.score_percent:.1f}%)")
                if Path(res.file_path).exists():
                    st.image(res.file_path, use_container_width=True)
                st.write(f"**{res.title}**")
                st.caption(f"유사도: `{res.similarity:.4f}`")


# =============================================================
# 탭 4: 신규 이미지 보관함 등록
# =============================================================
with tab4:
    st.subheader("➕ 신규 이미지 보관함 등록 (실시간 인덱싱)")
    st.markdown(
        "임의의 새로운 이미지 파일을 등록하면, **Vision API가 즉시 시각 설명을 생성**하고 "
        "**임베딩 벡터를 추출하여 보관함에 영구 추가**합니다. 이후 즉시 텍스트 검색 대상에 포함됩니다!"
    )

    new_img_file = st.file_uploader(
        "등록할 새 이미지 선택",
        type=["bmp", "png", "jpg", "jpeg", "webp"],
        key="new_img_uploader"
    )
    new_title = st.text_input("이미지 제목 (선택 사항):", placeholder="예: 해질녘의 한강 공원")

    if new_img_file and st.button("🚀 보관함에 등록 및 색인 추가", type="primary"):
        save_path = engine.image_dir / new_img_file.name
        with open(save_path, "wb") as f:
            f.write(new_img_file.read())

        with st.spinner(f"'{new_img_file.name}' Vision 분석 및 임베딩 생성 중..."):
            added_item = engine.add_custom_image(save_path, title=new_title if new_title.strip() else None)

        st.success(f"🎉 '{added_item.title}' 이미지가 보관함에 성공적으로 등록되었습니다!")
        st.image(added_item.file_path, caption=added_item.title, width=320)
        st.write(f"**생성된 시각 설명:** {added_item.description}")
        st.caption(f"현재 보관함 총 이미지 수: {len(engine.indexed_items)}개")
