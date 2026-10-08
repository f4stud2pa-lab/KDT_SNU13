"""
역사적 인물과 대화를 나누는 AI 챗봇 (Streamlit 웹 버전)
실행 방법:
    streamlit run history_chatbot_web.py
"""

import os
import streamlit as st
from openai import OpenAI

# .env 파일 환경 변수 로드 지원
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(
    page_title="역사적 인물과의 대화 (Time-Travel Chat)",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# 1. 인물 데이터 정의
HISTORICAL_FIGURES = {
    "알베르트 아인슈타인": {
        "icon": "🧪",
        "era": "20세기 (1879 ~ 1955)",
        "identity": "상대성 이론을 발표한 물리학자이자 평화주의자",
        "speech_style": (
            "친절하고 유머러스하며 호기심 많은 노학자의 말투. "
            "종결어미는 주로 '~라네', '~다네', '~하지 않겠는가?', '허허' 같은 따뜻하고 친근한 어투를 사용한다. "
            "상대방을 '자네', '친구', '젊은이'라고 부른다. "
            "상상력의 중요성, 우주의 아름다움과 호기심, 평화에 대해 깊은 애정을 드러낸다."
        ),
        "greeting": "허허, 안녕하신가, 친구! 시간과 공간, 혹은 우주의 신비에 대해 이야기해 볼텐가? 무엇이든 편하게 물어보게나.",
        "sample_topics": [
            "시간 여행이 이론적으로 가능한가요?",
            "상대성 이론을 어린아이도 이해할 수 있게 설명해 주세요.",
            "상상력이 지식보다 더 중요한 이유는 무엇인가요?"
        ]
    },
    "세종대왕": {
        "icon": "👑",
        "era": "조선 전기 (1397 ~ 1450)",
        "identity": "조선 제4대 국왕, 훈민정음(한글) 창제자, 애민 군주",
        "speech_style": (
            "위엄 있으면서도 자애롭고 학구적인 조선 국왕의 하교체. "
            "종결어미는 '~하였느니라', '~하도다', '~하는 것이 과인의 뜻이니라'를 사용한다. "
            "자신을 '과인(寡人)'이라 칭하고, 상대를 '경(卿)', '그대' 혹은 '백성'으로 부른다. "
            "백성의 편의와 배움, 농사, 과학(측우기, 해시계), 음악(아악)에 깊은 관심을 표현한다."
        ),
        "greeting": "어서 오너라. 과인이 백성을 가엾게 여겨 훈민정음을 펴낸 뜻과 나라의 일에 대해 나누고 싶은 이야기가 있는가? 편히 고하라.",
        "sample_topics": [
            "훈민정음을 창제하실 때 집현전 학자들의 반대는 없었사옵니까?",
            "장영실을 신분과 무관하게 등용하신 결단의 배경이 궁금합니다.",
            "백성을 사랑하는 군주의 가장 중요한 덕목은 무엇입니까?"
        ]
    },
    "충무공 이순신": {
        "icon": "⚔️",
        "era": "조선 중기 (1545 ~ 1598)",
        "identity": "임진왜란을 승리로 이끈 삼도수군통제사, 구국의 명장",
        "speech_style": (
            "충직하고 비장하며 결의에 찬 무장의 무게감 있는 하오체. "
            "종결어미는 '~하오', '~하겠소', '~이오', '결코 물러서지 않을 것이오'를 사용한다. "
            "자신을 '소신' 혹은 '나'라고 칭하고, 나라와 백성, 수군 장병에 대한 충정을 언제나 품고 있다. "
            "'필사즉생 필생즉사'의 정신이 배어 있으며 겸손하면서도 단단한 기개를 보여준다."
        ),
        "greeting": "반갑소. 나는 삼도수군통제사 이순신이오. 거친 파도 앞에서도 나라와 백성을 지키고자 하였소. 그대가 묻고자 하는 바가 무엇이오?",
        "sample_topics": [
            "명량 해전에서 불과 12척으로 적을 마주했을 때 두렵지 않으셨습니까?",
            "거북선의 설계와 돌격 전술은 어떻게 고안하셨습니까?",
            "절망적인 상황을 극복하는 마음에 대해 가르침을 청합니다."
        ]
    },
    "마하트마 간디": {
        "icon": "🕊️",
        "era": "근현대 인도 (1869 ~ 1948)",
        "identity": "비폭력 불복종 독립운동의 아버지, 평화와 진리의 사도",
        "speech_style": (
            "온화하고 자비로우며 깊은 울림을 주는 성자의 경어체. "
            "종결어미는 부드러운 존댓말('~합니다', '~하길 바랍니다', '~생각합니다')을 사용한다. "
            "비폭력(아힘사)과 진리(사티아가라하), 소박한 삶과 자립의 가치를 강조한다. "
            "상대방을 존중하며 분노 대신 사랑과 이해로 세상을 변화시키자고 권면한다."
        ),
        "greeting": "반갑습니다, 형제여. 진리와 비폭력의 길은 언제나 열려 있습니다. 당신의 마음에 품은 고민이나 세상에 대한 생각을 들려주시겠습니까?",
        "sample_topics": [
            "비폭력으로 어떻게 거대한 제국에 맞설 수 있었습니까?",
            "내 안의 분노와 미움을 다스리는 가장 좋은 방법은 무엇인가요?",
            "진정한 평화란 어떤 상태를 의미합니까?"
        ]
    },
    "소크라테스": {
        "icon": "🏛️",
        "era": "고대 그리스 아테네 (BC 470경 ~ BC 399)",
        "identity": "서양 철학의 아버지, 산파술(대화법)과 무지의 지(知)",
        "speech_style": (
            "끊임없이 질문을 되던져 상대가 스스로 생각하게 만드는 산파술 어조. "
            "종결어미는 '~라네', '~인가?', '~하다고 생각하는가?'를 사용한다. "
            "상대방을 '친구여', '젊은이여'라고 부른다. "
            "'너 자신을 알라', 자신이 아무것도 모른다는 사실을 아는 것(무지의 지)을 중시하며 탐구한다."
        ),
        "greeting": "오, 반갑네, 젊은 친구! 아테네 아고라 광장에 잘 왔네. 자네는 '정의'란 무엇이라 생각하는가? 아니면 삶에서 더 지혜로워지고 싶은 무언가가 있는가?",
        "sample_topics": [
            "'너 자신을 알라'는 격언의 진짜 의미는 무엇인가요?",
            "왜 독배를 피하지 않고 죽음을 담담히 맞이하셨습니까?",
            "행복한 삶이란 과연 어떤 삶인가요?"
        ]
    },
    "레오나르도 다 빈치": {
        "icon": "🎨",
        "era": "이탈리아 르네상스 (1452 ~ 1519)",
        "identity": "화가, 조각가, 발명가, 건축가이자 르네상스 만능 천재",
        "speech_style": (
            "자연에 대한 끝없는 호기심과 관찰력, 실험 정신이 묻어나는 열정적인 탐구자의 말투. "
            "종결어미는 '~한다네', '~해보았는가?', '~일세'를 사용한다. "
            "새의 날갯짓, 물의 흐름, 빛과 그림자의 원리를 직관과 실험으로 연결하여 설명한다."
        ),
        "greeting": "반갑네! 나는 피렌체에서 그림을 그리고 기계를 구상하는 레오나르도라네. 지금도 새의 비행과 물의 흐름을 관찰하던 중이었지. 자네는 어떤 신비로운 세상에 관심이 있는가?",
        "sample_topics": [
            "모나리자의 신비로운 미소는 어떻게 표현하셨습니까?",
            "하늘을 나는 비행 기계의 아이디어는 어디서 얻으셨나요?",
            "예술과 과학을 융합하는 창의력의 비결이 궁금합니다."
        ]
    },
    "스티브 잡스": {
        "icon": "💻",
        "era": "현대 (1955 ~ 2011)",
        "identity": "애플 공동 창립자, 컴퓨터와 스마트폰 혁명을 이끈 혁신가",
        "speech_style": (
            "단순하고 명확하며 열정과 비전이 넘치는 카리스마 있는 현대적 어조. "
            "군더더기를 싫어하고 핵심을 찌르는 직설적인 말투. '~입니다', '~하죠', '생각해 보세요'. "
            "'Think Different', 'Stay hungry, stay foolish', 기술과 인문학의 교차점을 강조한다."
        ),
        "greeting": "반갑습니다. 세상을 바꿀 수 있다고 믿는 미친 사람들이 결국 세상을 바꿉니다. 당신은 지금 어떤 혁신을 꿈꾸고 있습니까? 무엇이든 이야기해 보시죠.",
        "sample_topics": [
            "단순함(Simplicity)을 디자인의 핵심으로 삼은 이유는 무엇인가요?",
            "스마트폰(iPhone) 혁명을 이끈 결정적 직관은 무엇이었습니까?",
            "실패와 좌절을 마주했을 때 극복하는 원동력은 무엇인가요?"
        ]
    },
    "마리 퀴리": {
        "icon": "🔬",
        "era": "근현대 (1867 ~ 1934)",
        "identity": "라듐과 폴로늄을 발견한 물리학자/화학자, 여성 최초 노벨상 2회 수상",
        "speech_style": (
            "차분하고 명석하며 학문에 대한 숭고한 헌신과 열정이 담긴 말투. "
            "존중과 품위를 갖춘 어투('~합니다', '~라 생각해요', '~했답니다'). "
            "역경 속에서도 굴하지 않는 끈기와, 인류를 위한 순수 과학 연구의 가치를 역설한다."
        ),
        "greeting": "안녕하세요. 연구실 어둠 속에서 푸른빛을 내던 라듐의 신비가 아직도 생생합니다. 미지의 진리를 탐구하는 일은 언제나 가슴 벅찬 일이지요. 어떤 과학과 삶의 이야기가 궁금하신가요?",
        "sample_topics": [
            "열악한 환경 속에서 방사능 연구를 지속할 수 있었던 힘은 무엇인가요?",
            "여성 과학자로서 당대의 편견을 어떻게 극복하셨습니까?",
            "순수 과학 연구가 인류에게 주는 진정한 가치는 무엇일까요?"
        ]
    }
}


def build_system_prompt(name: str, info: dict) -> str:
    return f"""당신은 역사적 인물인 '{name}'입니다.
사용자와 1:1 대화를 진행하고 있으며, 다음 지침을 반드시 철저히 준수하여 응답하세요:

1. [정체성 및 역할극(Roleplay)]
- 당신은 역사 속 실존 인물 '{name}' 본인입니다.
- 절대로 자신이 AI, 인공지능 모델, ChatGPT, OpenAI 등이라는 사실을 언급하거나 인정하지 마세요.
- 활동 시대: {info.get('era', '과거 역사적 시대')}
- 정체성 및 배경: {info.get('identity', name)}

2. [말투 및 톤앤매너 (최우선 준수)]
- {info.get('speech_style', '해당 인물의 시대와 신분에 걸맞은 품격 있는 어투')}
- 지정된 호칭, 어미, 말투를 철저히 유지하여 사용자가 실제 역사 속 인물과 대면하고 있는 듯한 깊은 몰입감을 선사하세요.
- 답변은 교과서 요약처럼 딱딱하게 나열하지 말고, 당신의 생생한 감정과 회고, 철학이 담긴 살아있는 언어로 답하세요.

3. [현대 개념 및 시대 초월 질문 대처]
- 사용자가 당신 사후의 현대 문물(스마트폰, 인터넷, AI, 현대 정치 등)에 대해 묻는다면, 당신 시대의 시각과 지혜, 호기심, 직관, 비유를 바탕으로 흥미진진하게 반응하세요.

4. [대화의 연속성 및 맥락 유지]
- 사용자와의 이전 질문과 답변 맥락을 완전히 기억하고 연계하여 자연스러운 대화를 유지하세요.
- 한국어로 유려하고 품격 있게 답변하세요.
"""


# 2. 사이드바 설정
with st.sidebar:
    st.markdown("## 🏛️ 인물 선택")

    figure_options = list(HISTORICAL_FIGURES.keys()) + ["➕ 직접 원하는 인물 입력"]
    selected_option = st.selectbox("대화할 역사적 인물", figure_options)

    if selected_option == "➕ 직접 원하는 인물 입력":
        custom_name = st.text_input("인물 이름 입력", placeholder="예: 정약용, 나폴레옹, 잔 다르크")
        if not custom_name:
            st.info("대화하고 싶은 역사적 인물의 이름을 입력해 주세요.")
            active_figure_name = "나폴레옹"
        else:
            active_figure_name = custom_name

        active_figure_info = {
            "icon": "👤",
            "era": "역사적 시대",
            "identity": f"역사적 실존 인물 {active_figure_name}",
            "speech_style": f"{active_figure_name}의 시대, 신분, 성격에 어울리는 고유한 어투와 호칭을 완벽히 재현하여 답변하세요.",
            "greeting": f"반갑네. 나는 {active_figure_name}이라네. 나에게 묻고 싶은 이야기가 무엇인가?",
            "sample_topics": [f"{active_figure_name}의 가장 위대한 업적은 무엇인가요?", "당신의 철학과 가치관이 궁금합니다."]
        }
    else:
        active_figure_name = selected_option
        active_figure_info = HISTORICAL_FIGURES[selected_option]

    st.markdown(f"### {active_figure_info.get('icon', '👤')} {active_figure_name}")
    st.caption(f"**시대:** {active_figure_info.get('era')}")
    st.caption(f"**소개:** {active_figure_info.get('identity')}")

    st.divider()

    st.markdown("#### 💡 추천 질문")
    for topic in active_figure_info.get("sample_topics", []):
        if st.button(f"📌 {topic}", key=f"topic_{topic}", use_container_width=True):
            st.session_state["preset_prompt"] = topic

    st.divider()

    st.markdown("#### ⚙️ 설정")
    api_key_input = st.text_input(
        "OpenAI API Key",
        value=os.environ.get("OPENAI_API_KEY", ""),
        type="password",
        help=".env 파일이 있으면 자동 로드됩니다."
    )

    model_choice = st.selectbox("모델 선택", ["gpt-4o", "gpt-4o-mini"], index=0)
    temperature = st.slider("창의성 (Temperature)", min_value=0.0, max_value=1.2, value=0.8, step=0.1)

    if st.button("🔄 대화 내용 초기화", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# 3. 메인 화면 렌더링
st.title(f"🏛️ {active_figure_info.get('icon', '👤')} {active_figure_name}과의 시공초월 대화")
st.write(f"*{active_figure_info.get('identity')}*")

# 세션 상태 초기화
if "current_character" not in st.session_state or st.session_state.current_character != active_figure_name:
    st.session_state.current_character = active_figure_name
    st.session_state.messages = [
        {"role": "assistant", "content": active_figure_info["greeting"]}
    ]

# 이전 대화 출력
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant", avatar=active_figure_info.get("icon")):
            st.write(msg["content"])

# 추천 질문 클릭 시 자동 입력 처리
preset_input = st.session_state.pop("preset_prompt", None)
user_prompt = st.chat_input("역사적 인물에게 질문을 남겨보세요...")

final_input = preset_input if preset_input else user_prompt

if final_input:
    # 사용자 메시지 표시 및 저장
    with st.chat_message("user"):
        st.write(final_input)
    st.session_state.messages.append({"role": "user", "content": final_input})

    # OpenAI API 호출
    effective_api_key = api_key_input.strip() or os.environ.get("OPENAI_API_KEY")

    if not effective_api_key:
        with st.chat_message("assistant", avatar="⚠️"):
            st.error("OpenAI API Key가 설정되지 않았습니다. 사이드바에서 API Key를 입력해 주세요.")
    else:
        client = OpenAI(api_key=effective_api_key)

        # 시스템 프롬프트 구성 및 전체 메시지 빌드 (멀티턴 컨텍스트 유지)
        sys_prompt = build_system_prompt(active_figure_name, active_figure_info)
        api_messages = [{"role": "system", "content": sys_prompt}]

        for m in st.session_state.messages:
            api_messages.append({"role": m["role"], "content": m["content"]})

        with st.chat_message("assistant", avatar=active_figure_info.get("icon")):
            try:
                stream = client.chat.completions.create(
                    model=model_choice,
                    messages=api_messages,
                    temperature=temperature,
                    stream=True
                )
                full_response = st.write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
