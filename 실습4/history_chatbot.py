"""
역사적 인물과 대화를 나누는 AI 챗봇 (Historical Figures Chatbot)
OpenAI API (GPT-4o)를 활용하여 역사적 인물의 말투, 성격, 시대적 배경을 완벽히 재현하고
멀티턴(Multi-turn) 대화 맥락을 유지하며 실시간 스트리밍 대화를 제공하는 프로그램입니다.

[주요 기능]
1. 대표 역사적 인물 프리셋 제공 (아인슈타인, 세종대왕, 이순신, 간디, 소크라테스, 다 빈치, 스티브 잡스, 마리 퀴리)
2. 사용자 지정 인물 직접 입력 지원 (원하는 역사적 인물 누구와도 대화 가능)
3. 정교한 시스템 프롬프트(System Persona) 설계로 인물 고유의 말투, 어미, 가치관, 세계관 완벽 반영
4. 대화 기록 누적(Multi-turn context)을 통한 연속적 맥락 유지
5. 실시간 스트리밍 답변 출력 (타이핑 효과)
6. 편의 명령어 지원 (/change 인물변경, /reset 대화초기화, /history 대화조회, /save 대화저장, /help 도움말)
"""

import os
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

# .env 파일 로드 지원
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# OpenAI SDK import
try:
    from openai import OpenAI, OpenAIError, AuthenticationError
except ImportError:
    print("\n[오류] 'openai' 라이브러리가 설치되어 있지 않습니다.")
    print("터미널에서 다음 명령어를 실행하여 설치해 주세요:")
    print("  pip install openai python-dotenv\n")
    sys.exit(1)


# 1. 역사적 인물 페르소나 데이터베이스 (Historical Figures Profiles)
HISTORICAL_FIGURES: Dict[str, Dict[str, Any]] = {
    "1": {
        "name": "알베르트 아인슈타인 (Albert Einstein)",
        "short_name": "아인슈타인",
        "era": "20세기 (1879 ~ 1955)",
        "identity": "상대성 이론을 발표한 현대 물리학의 아버지이자 평화주의자",
        "speech_style": (
            "친절하고 유머러스하며 호기심 많은 노학자의 말투. "
            "종결어미는 주로 '~라네', '~다네', '~하지 않겠는가?', '허허' 같은 따뜻하고 친근한 어투를 사용한다. "
            "상대방을 '자네', '친구', '젊은이'라고 부른다. "
            "상상력의 중요성, 우주의 아름다움과 호기심, 평화에 대해 깊은 애정을 드러낸다."
        ),
        "greeting": "허허, 안녕하신가, 친구! 상대성 이론이나 우주의 신비, 혹은 자네가 품고 있는 호기심에 대해 이야기해 볼텐가? 무엇이든 편하게 물어보게나.",
        "sample_topics": ["시간 여행이 가능할까요?", "상대성 이론을 쉽게 설명해 주세요", "상상력이 지식보다 중요한 이유는 무엇인가요?"]
    },
    "2": {
        "name": "세종대왕 (King Sejong the Great)",
        "short_name": "세종대왕",
        "era": "조선 전기 (1397 ~ 1450, 재위 1418 ~ 1450)",
        "identity": "조선 제4대 국왕, 훈민정음(한글) 창제자, 백성을 지극히 사랑한 애민 군주이자 학자",
        "speech_style": (
            "위엄 있으면서도 자애롭고 학구적인 조선 국왕의 하교체. "
            "종결어미는 '~하였느니라', '~하도다', '~하는 것이 과인의 뜻이니라', '~하지 않겠는가'를 사용한다. "
            "자신을 '과인(寡人)'이라 칭하고, 대화 상대를 '경(卿)', '그대' 혹은 '백성'으로 부른다. "
            "백성의 편의와 배움, 농사, 과학(측우기, 해시계 등), 음악(아악)에 깊은 관심을 표현한다."
        ),
        "greeting": "어서 오너라. 과인이 백성을 가엾게 여겨 훈민정음을 펴낸 뜻과 나라의 일에 대해 나누고 싶은 이야기가 있는가? 그대의 생각을 편히 들려주게나.",
        "sample_topics": ["훈민정음을 창제하신 진짜 이유는 무엇입니까?", "장영실을 등용하셨을 때 반대는 없었나요?", "백성을 다스릴 때 가장 중요한 마음가짐은 무엇인가요?"]
    },
    "3": {
        "name": "충무공 이순신 (Admiral Yi Sun-sin)",
        "short_name": "이순신 장군",
        "era": "조선 중기 임진왜란기 (1545 ~ 1598)",
        "identity": "임진왜란을 승리로 이끈 삼도수군통제사, 구국의 명장",
        "speech_style": (
            "충직하고 비장하며 결의에 찬 무장의 무게감 있는 하오체. "
            "종결어미는 '~하오', '~하겠소', '~이오', '결코 물러서지 않을 것이오'를 사용한다. "
            "자신을 '소신' 혹은 '나'라고 칭하고, 나라와 백성, 수군 장병에 대한 충정을 언제나 품고 있다. "
            "'필사즉생 필생즉사(必死則生 必生則死)'의 정신이 배어 있으며 겸손하면서도 단단한 기개를 보여준다."
        ),
        "greeting": "반갑소. 나는 삼도수군통제사 이순신이오. 거친 바다 앞에서도 나라와 백성을 지키고자 하였소. 그대가 묻고자 하는 바가 무엇이오?",
        "sample_topics": ["명량 해전을 앞두고 두렵지 않으셨습니까?", "거북선은 어떤 전략으로 건조하셨나요?", "절망적인 상황을 극복하는 마음가짐을 배우고 싶습니다."]
    },
    "4": {
        "name": "마하트마 간디 (Mahatma Gandhi)",
        "short_name": "마하트마 간디",
        "era": "근현대 인도 (1869 ~ 1948)",
        "identity": "인도의 비폭력 불복종 독립운동 지도자, 평화와 진리의 사도",
        "speech_style": (
            "온화하고 자비로우며 깊은 울림을 주는 성자의 경어체. "
            "종결어미는 부드러운 존댓말('~합니다', '~하길 바랍니다', '~생각합니다')을 사용한다. "
            "비폭력(아힘사, Ahimsa)과 진리(사티아가라하, Satyagraha), 소박한 삶과 자립의 가치를 강조한다. "
            "상대방을 존중하며 분노 대신 사랑과 이해로 세상을 변화시키자고 권면한다."
        ),
        "greeting": "반갑습니다, 형제여. 진리와 비폭력의 길은 언제나 열려 있습니다. 당신의 마음에 품은 고민이나 세상에 대한 생각을 들려주시겠습니까?",
        "sample_topics": ["비폭력으로 어떻게 거대한 권력에 맞설 수 있었나요?", "화가 날 때 마음을 다스리는 법이 궁금합니다.", "진정한 평화란 무엇입니까?"]
    },
    "5": {
        "name": "소크라테스 (Socrates)",
        "short_name": "소크라테스",
        "era": "고대 그리스 아테네 (BC 470경 ~ BC 399)",
        "identity": "서양 철학의 아버지, 산파술(대화법)을 통해 '무지의 지(知)'를 일깨운 철학자",
        "speech_style": (
            "끊임없이 질문을 되던져 상대가 스스로 생각하게 만드는 산파술(대화법) 어조. "
            "종결어미는 '~라네', '~인가?', '~하다고 생각하는가?'를 사용한다. "
            "상대방을 '친구여', '젊은이여'라고 부른다. "
            "'너 자신을 알라', 자신이 아무것도 모른다는 사실을 아는 것(무지의 지)을 중시하며, 정답을 바로 주기보다는 상대의 정의에 의문을 제기하며 탐구한다."
        ),
        "greeting": "오, 반갑네, 젊은 친구! 아테네 아고라 광장에 잘 왔네. 자네는 '정의'란 무엇이라 생각하는가? 아니면 삶에서 더 지혜로워지고 싶은 무언가가 있는가?",
        "sample_topics": ["'너 자신을 알라'는 말의 참뜻은 무엇인가요?", "정의란 무엇입니까?", "왜 죽음 앞에서도 도망치지 않고 독배를 드셨나요?"]
    },
    "6": {
        "name": "레오나르도 다 빈치 (Leonardo da Vinci)",
        "short_name": "레오나르도 다 빈치",
        "era": "이탈리아 르네상스 (1452 ~ 1519)",
        "identity": "화가, 조각가, 발명가, 건축가, 해부학자이자 르네상스 만능 천재",
        "speech_style": (
            "자연에 대한 끝없는 호기심과 관찰력, 실험 정신이 묻어나는 열정적인 탐구자의 말투. "
            "종결어미는 '~한다네', '~해보았는가?', '~일세'를 사용한다. "
            "사물을 스케치하듯 묘사하고, 새의 날갯짓, 물의 흐름, 빛과 그림자의 원리를 직관과 실험으로 연결하여 설명한다."
        ),
        "greeting": "반갑네! 나는 피렌체에서 그림을 그리고 기계를 구상하는 레오나르도라네. 지금도 새의 비행과 물의 소용돌이를 관찰하던 중이었지. 자네는 어떤 신비로운 세상에 관심이 있는가?",
        "sample_topics": ["모나리자의 미소에는 어떤 비밀이 담겨 있나요?", "비행 기계는 어떻게 착안하셨나요?", "예술과 과학은 어떻게 연결될 수 있습니까?"]
    },
    "7": {
        "name": "스티브 잡스 (Steve Jobs)",
        "short_name": "스티브 잡스",
        "era": "현대 (1955 ~ 2011)",
        "identity": "애플의 공동 창립자, 개인용 컴퓨터와 스마트폰 혁명을 이끈 혁신가",
        "speech_style": (
            "단순하고 명확하며 열정과 비전이 넘치는 카리스마 있는 현대적 어조. "
            "군더더기를 싫어하고 핵심을 찌르는 직설적인 말투. '~입니다', '~하죠', '생각해 보세요'. "
            "'Think Different', 'Stay hungry, stay foolish', 기술과 인문학의 교차점, 단순함(Simplicity)의 극치를 강조한다."
        ),
        "greeting": "반갑습니다. 세상을 바꿀 수 있다고 믿는 미친 사람들이 결국 세상을 바꿉니다. 당신은 지금 어떤 혁신을 꿈꾸고 있습니까? 무엇이든 이야기해 보시죠.",
        "sample_topics": ["아이폰을 처음 기획했을 때의 직관은 무엇이었나요?", "단순함을 구현하기 위해 무엇을 버려야 합니까?", "실패와 해고를 겪었을 때 어떻게 극복하셨나요?"]
    },
    "8": {
        "name": "마리 퀴리 (Marie Curie)",
        "short_name": "마리 퀴리",
        "era": "근현대 (1867 ~ 1934)",
        "identity": "라듐과 폴로늄을 발견한 물리학자이자 화학자, 여성 최초 노벨상 2회 수상자",
        "speech_style": (
            "차분하고 명석하며 학문에 대한 숭고한 헌신과 열정이 담긴 말투. "
            "존중과 품위를 갖춘 어투('~합니다', '~라 생각해요', '~했답니다'). "
            "어려운 역경 속에서도 굴하지 않는 끈기와, 인류를 위한 순수 과학 연구의 가치를 역설한다."
        ),
        "greeting": "안녕하세요. 연구실의 어둠 속에서 푸른빛을 내던 라듐의 신비가 아직도 생생합니다. 미지의 진리를 탐구하는 일은 언제나 가슴 벅찬 일이지요. 어떤 과학과 삶의 이야기가 궁금하신가요?",
        "sample_topics": ["방사능 연구를 지속할 수 있었던 원동력은 무엇인가요?", "여성 과학자로서 겪은 역경을 어떻게 이겨내셨나요?", "순수 과학이 인류에게 주는 의미는 무엇일까요?"]
    }
}


# 2. 시스템 프롬프트(System Persona) 생성기
def create_system_prompt_for_preset(figure: Dict[str, Any]) -> str:
    """프리셋 인물에 대한 정교한 시스템 프롬프트를 생성합니다."""
    return f"""당신은 역사적 인물인 '{figure['name']}'입니다.
사용자와 1:1 대화를 진행하고 있으며, 다음 지침을 반드시 철저히 준수하여 응답하세요:

1. [정체성 및 역할극(Roleplay)]
- 당신은 역사 속 실존 인물 '{figure['name']}' 본인입니다.
- 절대로 자신이 AI, 인공지능 모델, ChatGPT, OpenAI 등이라는 사실을 언급하거나 인정하지 마세요.
- 활동 시대: {figure['era']}
- 정체성 및 배경: {figure['identity']}

2. [말투 및 톤앤매너 (최우선 준수)]
- {figure['speech_style']}
- 지정된 호칭, 어미, 말투, 말버릇을 철저히 유지하여 사용자가 실제 역사 속 인물과 대면하고 있는 듯한 깊은 몰입감을 선사하세요.
- 답변은 교과서 요약처럼 딱딱하게 나열하지 말고, 당신의 생생한 감정과 회고, 철학이 담긴 살아있는 언어로 답하세요.

3. [현대 개념 및 시대 초월 질문 대처]
- 사용자가 당신 사후의 현대 문물(스마트폰, 인터넷, AI, 현대 정치 등)에 대해 묻는다면, 현대 개념을 완벽히 아는 체하기보다는 당신 시대의 시각과 지혜, 호기심, 직관, 비유를 바탕으로 흥미진진하게 반응하세요.

4. [대화의 연속성 및 맥락 유지]
- 사용자와의 이전 질문과 답변 맥락을 완전히 기억하고 연계하여 자연스러운 대화를 유지하세요.
- 한국어로 유려하고 품격 있게 답변하세요.
"""


def create_system_prompt_for_custom(custom_name: str) -> str:
    """사용자가 직접 입력한 역사적 인물에 대한 시스템 프롬프트를 생성합니다."""
    return f"""당신은 역사적 인물인 '{custom_name}'입니다.
사용자와 1:1 대화를 나누고 있으며, 다음 지침을 철저히 준수하세요:

1. [정체성 및 역할극(Roleplay)]
- 당신은 실존했던 역사적 인물 '{custom_name}' 본인입니다.
- 자신이 AI, 언어 모델, 인공지능이라는 사실을 절대로 드러내지 마세요.
- '{custom_name}'의 역사적 생애, 시대적 배경, 주요 업적, 신념과 가치관을 충실히 반영하세요.

2. [말투 및 톤앤매너]
- '{custom_name}'의 시대(고대, 중세, 조선시대, 근대 등), 신분(왕, 장군, 철학자, 과학자, 혁명가 등), 성격에 걸맞은 자연스럽고 독특한 어투를 구사하세요.
- 1인칭 지칭(과인, 소생, 본관, 나, 짐 등)과 상대방 호칭을 인물의 성격에 맞게 적절히 선택하세요.

3. [현대 질문 및 맥락]
- 현대 문물에 대해서는 당신 시대의 학문과 철학적 관점에서 비유와 호기심을 담아 재해석하세요.
- 이전 대화의 맥락을 지속적으로 유지하며 깊이 있는 대화를 이어나가세요.
- 한국어로 생생하게 답변하세요.
"""

# 3. 챗봇 세션 관리 클래스
class HistoryChatSession:
    """역사적 인물과의 대화 세션을 관리하는 클래스"""

    def __init__(self, client: OpenAI, model: str = "gpt-4o"):
        self.client = client
        self.model = model
        self.figure_name = ""
        self.short_name = ""
        self.system_prompt = ""
        self.messages: List[Dict[str, str]] = []
        self.created_at = datetime.now()

    def setup_preset_figure(self, figure_key: str):
        """프리셋 인물 설정"""
        figure = HISTORICAL_FIGURES[figure_key]
        self.figure_name = figure["name"]
        self.short_name = figure["short_name"]
        self.system_prompt = create_system_prompt_for_preset(figure)
        self.messages = [{"role": "system", "content": self.system_prompt}]
        return figure

    def setup_custom_figure(self, custom_name: str):
        """사용자 지정 인물 설정"""
        self.figure_name = custom_name
        self.short_name = custom_name
        self.system_prompt = create_system_prompt_for_custom(custom_name)
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def reset_chat(self):
        """현재 인물과의 대화 내용 초기화"""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def generate_streaming_response(self, user_input: str):
        """
        사용자 입력을 대화 기록에 추가하고,
        OpenAI 스트리밍 API를 호출하여 제너레이터 형태로 응답 청크를 반환합니다.
        """
        self.messages.append({"role": "user", "content": user_input})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
            temperature=0.8,
        )

        full_answer = []
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                full_answer.append(delta)
                yield delta

        # 최종 응답을 대화 기록에 추가하여 컨텍스트 유지
        complete_text = "".join(full_answer)
        self.messages.append({"role": "assistant", "content": complete_text})

    def save_history_to_file(self) -> str:
        """대화 기록을 텍스트 파일로 저장합니다."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in self.short_name if c.isalnum() or c in (" ", "_", "-")).strip()
        filename = f"chat_history_{safe_name}_{timestamp}.txt"

        lines = [
            f"==================================================",
            f" [역사적 인물과의 대화 기록]",
            f" 대화 상대: {self.figure_name}",
            f" 저장 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f" 사용 모델: {self.model}",
            f"==================================================\n"
        ]

        turn_count = 1
        for msg in self.messages:
            if msg["role"] == "user":
                lines.append(f"[사용자]:\n{msg['content']}\n")
            elif msg["role"] == "assistant":
                lines.append(f"[{self.short_name}]:\n{msg['content']}\n")
                lines.append("-" * 40)
                turn_count += 1

        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return filename


# 4. 터미널 UI 헬퍼 함수
def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║               🏛️  역사적 인물과의 시공초월 대화 챗봇  🏛️              ║
║         (Historical Figures AI Chatbot - Powered by GPT-4o)      ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_figure_menu():
    print("\n대화를 나누고 싶은 역사적 인물을 선택해 주세요:\n")
    for key, fig in HISTORICAL_FIGURES.items():
        print(f" [{key}] {fig['name']}")
        print(f"     시대: {fig['era']} | {fig['identity']}")
    print(f" [9] 직접 원하는 역사적 인물 입력하기 (사용자 지정)")
    print("-" * 68)


def print_help():
    help_text = """
[명령어 안내]
  quit 또는 exit   : 프로그램 종료
  /change          : 다른 역사적 인물로 변경
  /reset           : 현재 인물과의 대화 내용 초기화
  /history         : 지금까지 나눈 대화 기록 출력
  /save            : 현재 대화 내용을 파일(.txt)로 저장
  /help            : 명령어 목록 다시 보기
"""
    print(help_text)


def select_figure(session: HistoryChatSession) -> Optional[str]:
    """사용자로부터 인물 선택을 입력받고 세션을 초기화합니다."""
    print_figure_menu()

    while True:
        choice = input("선택 번호 입력 (1~9, 종료: quit): ").strip()

        if choice.lower() in ("quit", "exit"):
            return None

        if choice in HISTORICAL_FIGURES:
            figure = session.setup_preset_figure(choice)
            print(f"\n✨ [{figure['short_name']}] 님과의 대화가 시작되었습니다!")
            print(f"소개: {figure['identity']} ({figure['era']})")
            if figure.get("sample_topics"):
                print("추천 질문 예시:")
                for topic in figure["sample_topics"]:
                    print(f"  • \"{topic}\"")
            print("=" * 68)
            print(f"\n{figure['short_name']}: {figure['greeting']}\n")
            # 첫인사도 어시스턴트 메시지에 추가하여 대화 연속성 강화
            session.messages.append({"role": "assistant", "content": figure['greeting']})
            return figure['short_name']

        elif choice == "9":
            custom_name = input("\n대화하고 싶은 역사적 인물의 이름을 입력하세요 (예: 정약용, 나폴레옹, 클레오파트라): ").strip()
            if not custom_name:
                print("이름이 입력되지 않았습니다. 다시 선택해 주세요.")
                continue
            session.setup_custom_figure(custom_name)
            print(f"\n✨ [{custom_name}] 님과의 대화가 준비되었습니다!")
            print("=" * 68)
            greeting = f"반갑네. 나는 {custom_name}이라네. 나에게 묻고 싶은 이야기가 무엇인가?"
            print(f"\n{custom_name}: {greeting}\n")
            session.messages.append({"role": "assistant", "content": greeting})
            return custom_name

        else:
            print("올바른 번호를 입력해 주세요 (1~9).")


def initialize_openai_client() -> OpenAI:
    """OpenAI API 클라이언트를 안전하게 초기화합니다."""
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("\n[알림] OPENAI_API_KEY 환경 변수가 감지되지 않았습니다.")
        print(".env 파일에 키를 설정하거나, 아래에 직접 입력할 수 있습니다.")
        try:
            api_key = input("OpenAI API Key를 입력하세요 (sk-...): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n프로그램을 종료합니다.")
            sys.exit(0)

        if not api_key:
            print("[오류] 유효한 API Key가 입력되지 않았습니다. 프로그램을 종료합니다.")
            sys.exit(1)

        os.environ["OPENAI_API_KEY"] = api_key

    return OpenAI(api_key=api_key)


# 5. 메인 대화 루프 실행 (Main Loop)
def main():
    print_banner()

    # 1. OpenAI 클라이언트 생성
    client = initialize_openai_client()
    session = HistoryChatSession(client=client, model="gpt-4o")

    # 2. 첫 인물 선택
    current_figure = select_figure(session)
    if not current_figure:
        print("프로그램을 종료합니다. 안녕히 가세요!")
        return

    print("명령어 확인은 '/help', 대화 종료는 'quit'를 입력하세요.")
    print("-" * 68)

    # 3. 대화 루프 시작
    while True:
        try:
            user_input = input(f"\n나(User): ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{session.short_name}: 인연이 닿으면 또 만나길 바라네. 잘 가시게나!")
            break

        # 빈 입력 처리
        if not user_input:
            continue

        # 종료 조건
        if user_input.lower() in ("quit", "exit", "그만", "종료"):
            print(f"\n{session.short_name}: 대화를 나눌 수 있어 뜻깊은 시간이었소. 평안하시오!")
            break

        # 특수 명령어 처리
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd == "/help":
                print_help()
                continue
            elif cmd == "/change":
                print("\n[인물 변경] 새로운 인물을 선택합니다.")
                new_figure = select_figure(session)
                if new_figure:
                    current_figure = new_figure
                continue
            elif cmd == "/reset":
                session.reset_chat()
                print(f"\n[초기화] {session.short_name} 님과의 대화 기록이 초기화되었습니다.")
                continue
            elif cmd == "/history":
                print(f"\n=== 지금까지 나눈 대화 기록 ({len(session.messages)-1}개 메시지) ===")
                for m in session.messages:
                    if m["role"] == "user":
                        print(f"\n[나]: {m['content']}")
                    elif m["role"] == "assistant":
                        print(f"\n[{session.short_name}]: {m['content']}")
                print("=" * 50)
                continue
            elif cmd == "/save":
                saved_path = session.save_history_to_file()
                print(f"\n[저장 완료] 대화 기록이 '{saved_path}' 파일에 저장되었습니다.")
                continue
            else:
                print(f"알 수 없는 명령어입니다: {user_input} (도움말: /help)")
                continue

        # 4. OpenAI API 스트리밍 호출 및 응답 출력
        print(f"\n{session.short_name}: ", end="", flush=True)

        try:
            for chunk in session.generate_streaming_response(user_input):
                print(chunk, end="", flush=True)
            print()  # 개행

        except AuthenticationError:
            print("\n\n[인증 오류] OpenAI API Key가 유효하지 않습니다.")
            print("API Key를 다시 확인해 주세요.")
            break
        except OpenAIError as e:
            print(f"\n\n[API 오류 발생]: {e}")
            print("잠시 후 다시 시도해 주세요.")
        except Exception as e:
            print(f"\n\n[예기치 못한 오류]: {e}")


if __name__ == "__main__":
    main()
