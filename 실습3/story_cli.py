#!/usr/bin/env python3
"""
그림과 감정 기반 이야기 생성 CLI 프로그램 (Command Line Interface)
사용법:
  1. 대화형 모드:
     python story_cli.py
  2. 인자 전달 모드:
     python story_cli.py --images img1.jpg img2.jpg img3.jpg --sentiment 행복
"""

import argparse
import os
import sys
from pathlib import Path

# story_engine 가져오기
from story_engine import StoryEngine, SENTIMENT_PROFILES

# dotenv 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def print_banner():
    banner = """
    그림과 감정을 기반으로 한 이야기 생성기 (Picture Storyteller)
  - 여러 장의 그림을 분석하여 하나의 자연스러운 서사로 연결합니다.
  - 선택한 감정(Sentiment)에 맞춰 스토리 템플릿과 어조를 반영합니다.
"""
    print(banner)


def select_sentiment_interactive() -> str:
    print("\n[단계 2] 이야기의 전체적인 감정(Sentiment)을 선택하세요:")
    sentiments = StoryEngine.get_supported_sentiments()
    for idx, s in enumerate(sentiments, start=1):
        info = SENTIMENT_PROFILES[s]
        print(f"  {idx}. {s:<4} ({info['english']}) - {info['tone']}")
    print(f"  {len(sentiments) + 1}. 직접 입력 (사용자 정의 감정)")

    while True:
        choice = input("\n원하는 감정의 번호 또는 감정 이름을 입력하세요: ").strip()
        if not choice:
            continue

        if choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(sentiments):
                return sentiments[num - 1]
            elif num == len(sentiments) + 1:
                custom = input("적용하고 싶은 감정을 입력하세요 (예: 아늑함, 신비로움, 희망찬): ").strip()
                if custom:
                    return custom
            else:
                print("잘못된 번호입니다. 다시 선택해 주세요.")
        else:
            # 직접 텍스트 입력인 경우
            return choice


def collect_images_interactive() -> list[str]:
    print("\n[단계 1] 이야기로 연결할 그림(이미지) 파일 경로들을 입력하세요.")
    print("  * 순서대로 이야기가 전개됩니다.")
    print("  * 여러 경로를 공백으로 구분하거나, 엔터를 치며 하나씩 입력할 수 있습니다.")
    print("  * 입력을 마치려면 빈 줄에서 엔터를 누르세요.\n")

    images = []
    first_line = input("이미지 경로 입력 (예: sample1.png sample2.png): ").strip()
    if first_line:
        # 공백 분리 시도
        parts = [p.strip().strip("'\"") for p in first_line.split() if p.strip()]
        for p in parts:
            if Path(p).is_file():
                images.append(p)
            else:
                print(f"  [경고] 파일을 찾을 수 없습니다: {p}")

    # 추가 입력 받기
    while True:
        line = input(f"추가 이미지 경로 (현재 {len(images)}개 등록됨, 완료 시 엔터): ").strip().strip("'\"")
        if not line:
            if len(images) > 0:
                break
            else:
                print("최소 1장 이상의 이미지가 필요합니다. 다시 입력해 주세요.")
                continue

        if Path(line).is_file():
            images.append(line)
            print(f"  -> 등록 완료: [그림 {len(images)}] {Path(line).name}")
        else:
            print(f"  [오류] 파일을 찾을 수 없습니다: {line}")

    return images


def format_output(result) -> str:
    lines = []
    lines.append("\n" + "=" * 65)
    lines.append(f" ✨ 완성된 이야기: {result.title}")
    lines.append("=" * 65)
    lines.append(f"• 선택된 감정: {result.sentiment}")
    lines.append(f"• 적용된 어조: {result.sentiment_profile.get('tone', '')}")
    lines.append("-" * 65)
    lines.append("\n[ 각 그림별 AI 분석 리포트 ]\n")

    for analysis in result.image_analyses:
        lines.append(f"  ▶ [그림 {analysis.index}] {analysis.summary}")
        lines.append(f"    - 주체/인물: {analysis.characters}")
        lines.append(f"    - 배경/장소: {analysis.background}")
        lines.append(f"    - 행동/사건: {analysis.action_or_event}")
        if analysis.key_details:
            lines.append(f"    - 시각적 특징: {', '.join(analysis.key_details)}")
        lines.append("")

    lines.append("-" * 65)
    lines.append("[ 스토리 전문 ]\n")
    lines.append(f"{result.story}\n")

    if result.moral_or_thought:
        lines.append(f"[한 줄 여운]: {result.moral_or_thought}")
    lines.append("=" * 65 + "\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="그림과 감정 기반 단편 이야기 생성 프로그램 (OpenAI Vision 활용)"
    )
    parser.add_argument(
        "-i", "--images",
        nargs="+",
        help="이야기로 연결할 이미지 파일 경로 목록 (순서대로 입력)"
    )
    parser.add_argument(
        "-s", "--sentiment",
        help="이야기의 중심 감정 (예: 행복, 슬픔, 긴장감, 설렘, 코믹, 감동 등)"
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API 키 (지정하지 않을 경우 환경변수 OPENAI_API_KEY 사용)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="API 호출 없이 샘플 목업 데이터로 시뮬레이션 실행"
    )
    parser.add_argument(
        "-o", "--output",
        help="결과를 저장할 텍스트 파일 경로"
    )

    args = parser.parse_args()

    print_banner()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    mock_mode = args.mock

    if not api_key and not mock_mode:
        print("[안내] OPENAI_API_KEY 환경변수가 감지되지 않았습니다.")
        choice = input("API 키 없이 모의(Mock) 시뮬레이션 모드로 실행하시겠습니까? (y/N): ").strip().lower()
        if choice in ("y", "yes"):
            mock_mode = True
        else:
            print("\n'.env' 파일에 OPENAI_API_KEY=sk-... 를 설정하거나,")
            print("export OPENAI_API_KEY='sk-...' 명령을 실행한 후 다시 시도해 주세요.")
            print("또는 '--mock' 옵션을 붙여 테스트할 수 있습니다.")
            sys.exit(1)

    # 1. 이미지 목록 확보
    images = args.images
    if not images:
        images = collect_images_interactive()
    else:
        # 유효성 검사
        valid_images = []
        for img in images:
            if Path(img).is_file():
                valid_images.append(img)
            else:
                print(f"[경고] 이미지 파일을 찾을 수 없습니다: {img}")
        if not valid_images:
            print("[오류] 유효한 이미지 파일이 없습니다.")
            sys.exit(1)
        images = valid_images

    # 2. 감정(Sentiment) 확보
    sentiment = args.sentiment
    if not sentiment:
        sentiment = select_sentiment_interactive()

    print("\n" + "-" * 65)
    print(f"🚀 이야기 생성을 시작합니다...")
    print(f"• 입력 이미지: {len(images)}장")
    for i, path in enumerate(images, start=1):
        print(f"  - 그림 {i}: {path}")
    print(f"• 선택된 감정: {sentiment}")
    print(f"• 실행 모드: {'[모의 시뮬레이션 (Mock)]' if mock_mode else '[OpenAI Vision (gpt-4o)]'}")
    print("-" * 65)

    try:
        engine = StoryEngine(api_key=api_key, mock_mode=mock_mode)
        result = engine.generate_story(images=images, sentiment=sentiment)
        output_text = format_output(result)
        print(output_text)

        # 결과 저장 여부
        save_path = args.output
        if not save_path and sys.stdin.isatty():
            ans = input("생성된 이야기를 파일로 저장하시겠습니까? (y/N): ").strip().lower()
            if ans in ("y", "yes"):
                save_path = input("저장할 파일명 입력 (기본값: generated_story.txt): ").strip()
                if not save_path:
                    save_path = "generated_story.txt"

        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(output_text)
            print(f"💾 결과가 성공적으로 저장되었습니다: {save_path}")

    except Exception as e:
        print(f"\n[오류 발생]: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
