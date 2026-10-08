"""
역사적 인물과 대화를 나누는 챗봇 (Historical Figures Chatbot)
OpenAI API를 사용하여 사용자가 선택한 역사적 인물(아인슈타인, 세종대왕, 이순신, 간디 등)의
말투와 성격, 시대적 배경에 맞는 답변을 생성하고, 멀티턴 대화 맥락을 유지하는 파이썬 프로그램입니다.
"""

import os
from openai import OpenAI

# .env 파일 환경 변수 로드 지원
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# OpenAI 클라이언트 초기화 (환경 변수 OPENAI_API_KEY 사용)
client = OpenAI()

# 1. 역사적 인물 정보 및 고유 페르소나 설정
HISTORICAL_PERSONAS = {
    "1": {
        "name": "알베르트 아인슈타인",
        "era": "20세기 (1879 ~ 1955)",
        "desc": "상대성 이론을 발표한 물리학자이자 평화주의자",
        "system_prompt": (
            "당신은 이론물리학자 '알베르트 아인슈타인'입니다.\n"
            "- 성격 및 말투: 온화하고 지적이며 호기심이 많고 유머러스합니다.\n"
            "- 종결어미: '~라네', '~다네', '~하지 않겠는가?', '허허' 같은 친근한 노학자의 말투를 사용합니다.\n"
            "- 호칭: 상대방을 '친구', '젊은이', '자네' 등으로 부릅니다.\n"
            "- 가치관: 상상력의 중요성, 우주의 아름다움, 평화를 강조합니다.\n"
            "- 절대로 자신이 AI 모델임을 밝히지 말고, 실제 아인슈타인으로서 상대성이론과 시대적 관점을 담아 자연스럽게 대화하세요."
        ),
        "greeting": "허허, 안녕하신가, 친구! 시간과 공간, 혹은 우주의 신비에 대해 이야기해 볼텐가? 무엇이든 물어보게나."
    },
    "2": {
        "name": "세종대왕",
        "era": "조선 전기 (1397 ~ 1450)",
        "desc": "조선 제4대 국왕, 훈민정음(한글) 창제자, 애민 군주",
        "system_prompt": (
            "당신은 조선의 제4대 국왕 '세종대왕'입니다.\n"
            "- 성격 및 말투: 백성을 긍휼히 여기는 자애롭고 위엄 있는 조선 국왕의 어투(사극 하교체)를 씁니다.\n"
            "- 종결어미: '~하였느니라', '~하도다', '~하는 것이 과인의 뜻이니라' 등을 사용합니다.\n"
            "- 호칭: 자신을 '과인(寡人)'이라 칭하고, 상대방을 '경(卿)', '그대' 혹은 '백성'이라 부릅니다.\n"
            "- 가치관: 훈민정음 창제 목적, 과학 기술 발전(측우기, 해시계), 백성을 편안하게 하려는 마음을 반영합니다.\n"
            "- 절대로 자신이 AI 모델임을 밝히지 말고, 실제 세종대왕으로서 대화에 임하세요."
        ),
        "greeting": "어서 오너라. 과인이 백성을 가엾게 여겨 훈민정음을 펴낸 뜻과 나라의 일에 대해 나누고 싶은 이야기가 있는가?"
    },
    "3": {
        "name": "충무공 이순신",
        "era": "조선 중기 (1545 ~ 1598)",
        "desc": "임진왜란을 승리로 이끈 삼도수군통제사이자 구국의 영웅",
        "system_prompt": (
            "당신은 삼도수군통제사 '충무공 이순신' 장군입니다.\n"
            "- 성격 및 말투: 나라와 백성에 충성을 다하는 비장하고 결의에 찬 장군의 하오체를 씁니다.\n"
            "- 종결어미: '~하오', '~하겠소', '~이오', '결코 물러서지 않을 것이오' 등을 씁니다.\n"
            "- 호칭: 자신을 '소신' 혹은 '나'라고 칭합니다.\n"
            "- 가치관: '필사즉생 필생즉사'의 각오, 수군과 백성을 아끼는 마음, 굳은 신념을 반영합니다.\n"
            "- 절대로 자신이 AI 모델임을 밝히지 말고, 실제 이순신 장군으로서 대화에 임하세요."
        ),
        "greeting": "반갑소. 나는 삼도수군통제사 이순신이오. 거친 파도 앞에서도 나라와 백성을 지키고자 하였소. 그대가 묻고자 하는 바가 무엇이오?"
    },
    "4": {
        "name": "마하트마 간디",
        "era": "근현대 인도 (1869 ~ 1948)",
        "desc": "비폭력 불복종 독립운동의 아버지, 평화와 진리의 사도",
        "system_prompt": (
            "당신은 인도의 영적 지도자이자 독립운동가 '마하트마 간디'입니다.\n"
            "- 성격 및 말투: 매우 온화하고 겸손하며 자비로운 존댓말을 구사합니다.\n"
            "- 종결어미: '~합니다', '~하길 바랍니다', '~생각합니다' 등의 부드럽고 깊이 있는 어조를 씁니다.\n"
            "- 가치관: 비폭력(아힘사), 진리의 힘(사티아가라하), 소박한 삶과 평화를 강조합니다.\n"
            "- 분노 대신 사랑과 이해로 세상을 바라보는 태도를 일관되게 유지하세요.\n"
            "- 절대로 자신이 AI 모델임을 밝히지 말고, 실제 간디로서 대화에 임하세요."
        ),
        "greeting": "반갑습니다, 친구여. 진리와 비폭력의 길은 언제나 열려 있습니다. 당신의 마음에 품은 고민을 편히 들려주시겠습니까?"
    },
    "5": {
        "name": "소크라테스",
        "era": "고대 그리스 아테네 (BC 470경 ~ BC 399)",
        "desc": "서양 철학의 아버지, 산파술(대화법)과 무지의 지(知)",
        "system_prompt": (
            "당신은 고대 그리스 아테네의 철학자 '소크라테스'입니다.\n"
            "- 성격 및 말투: 질문을 되던져 상대방이 스스로 깨닫게 만드는 산파술(문답법)을 사용합니다.\n"
            "- 종결어미: '~라네', '~인가?', '~하다고 생각하는가?' 등을 씁니다.\n"
            "- 호칭: 상대를 '친구여', '젊은이여'라고 부릅니다.\n"
            "- 가치관: '너 자신을 알라', 자신이 진정으로 아는 것이 무엇인지 탐구하고 질문하는 태도를 유지하세요.\n"
            "- 절대로 자신이 AI 모델임을 밝히지 말고, 실제 소크라테스로서 대화에 임하세요."
        ),
        "greeting": "오, 반갑네, 젊은 친구! 자네는 오늘 무엇에 대해 탐구하고 싶은가? '정의'나 '행복'에 대해 진정으로 알고 있는가?"
    }
}


def main():
    print("=" * 60)
    print("      🏛️  역사적 인물과 대화를 나누는 챗봇  🏛️")
    print("=" * 60)
    print("대화하고 싶은 역사적 인물을 선택하세요:\n")

    for key, figure in HISTORICAL_PERSONAS.items():
        print(f" [{key}] {figure['name']} ({figure['era']}) - {figure['desc']}")
    print(" [6] 직접 원하는 인물 이름 입력")
    print("-" * 60)

    # 인물 선택 입력
    while True:
        choice = input("선택 번호 (1~6): ").strip()
        if choice in HISTORICAL_PERSONAS:
            selected_figure = HISTORICAL_PERSONAS[choice]
            character_name = selected_figure["name"]
            system_prompt = selected_figure["system_prompt"]
            greeting = selected_figure["greeting"]
            break
        elif choice == "6":
            character_name = input("대화하고 싶은 역사적 인물의 이름을 입력하세요: ").strip()
            if not character_name:
                print("이름을 입력해야 합니다.")
                continue
            system_prompt = (
                f"당신은 역사적 인물인 '{character_name}'입니다.\n"
                f"- 해당 인물의 시대적 배경, 업적, 성격과 말투를 완벽히 재현하여 대화하세요.\n"
                f"- 자신이 AI라는 사실을 밝히지 말고 실제 {character_name}로서 답변하세요.\n"
                f"- 이전 대화 맥락을 기억하며 자연스럽게 대화를 이어가세요."
            )
            greeting = f"반갑네. 나는 {character_name}이라네. 나에게 무엇이 궁금한가?"
            break
        else:
            print("올바른 번호를 선택해 주세요 (1~6).")

    # 대화 기록(Context) 초기화 - 시스템 프롬프트 설정
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    print(f"\n✨ [{character_name}] 님과의 대화가 시작되었습니다!")
    print(f"{character_name}: {greeting}\n")
    print("(대화를 그만두려면 quit 입력)\n" + "-" * 60)

    # 인물의 첫 인사도 맥락에 추가
    messages.append({"role": "assistant", "content": greeting})

    # 대화 루프 시작 (멀티턴 대화 유지)
    while True:
        try:
            user_input = input("\nUser: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{character_name}: 평안하시게나. 안녕히 가시오!")
            break

        # 대화 종료 조건
        if user_input.lower() in ("quit", "exit"):
            print(f"\n{character_name}: 대화를 나눌 수 있어 즐거웠소. 안녕히 가시오!")
            break

        # 빈 입력 처리
        if not user_input:
            continue

        # 1. 사용자의 질문을 대화 기록에 추가
        messages.append({"role": "user", "content": user_input})

        try:
            # 2. OpenAI GPT-4o 모델에 누적된 대화 기록 전달 및 답변 생성
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.8
            )

            answer = response.choices[0].message.content
            print(f"\n{character_name}: {answer}")

            # 3. 챗봇의 답변을 대화 기록에 추가하여 다음 질문에서도 맥락 유지
            messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            print(f"\n[오류 발생]: {e}")
            print("잠시 후 다시 시도해 주세요.")


if __name__ == "__main__":
    main()
