"""
텍스트 쿼리 기반 이미지 검색 및 분류 CLI 프로그램 (image_search.py)
=====================================================================
사용자가 입력한 텍스트 쿼리 검색, 임의의 이미지 분류(Classification),
이미지 기반 유사 이미지 탐색, 신규 이미지 등록 기능을 제공합니다.
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from image_search_engine import (
    DEFAULT_CLASSIFICATION_CATEGORIES,
    ImageSearchEngine,
)


def open_file_in_viewer(filepath: str):
    """운영체제 기본 이미지 뷰어로 이미지를 엽니다."""
    try:
        path = Path(filepath).resolve()
        if not path.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {path}")
            return

        current_os = platform.system()
        if current_os == "Darwin":       # macOS
            subprocess.run(["open", str(path)], check=True)
        elif current_os == "Windows":    # Windows
            os.startfile(str(path))
        else:                            # Linux
            subprocess.run(["xdg-open", str(path)], check=True)
        print(f"🖼️ 이미지 뷰어로 열었습니다: {path.name}")
    except Exception as e:
        print(f"⚠️ 이미지 열기 실패: {e}")


def print_banner(engine: ImageSearchEngine):
    """프로그램 시작 배너를 출력합니다."""
    api_status = "🟢 OpenAI API 온라인 연동" if engine.is_api_ready() else "🟡 로컬 시맨틱 시뮬레이션 모드"
    print("\n" + "=" * 66)
    print(" 🔍 AI 이미지 검색 및 스마트 분류 시스템 (Search & Classifier)")
    print("=" * 66)
    print(f" • 운영 모드    : {api_status}")
    print(f" • 임베딩 모델  : {engine.embedding_model}")
    print(f" • Vision 모델 : {engine.vision_model}")
    print(f" • 이미지 보관함: {engine.image_dir} ({len(engine.indexed_items)}개 색인됨)")
    print("=" * 66)
    print(" 💡 지원 기능 및 명령어:")
    print("   1) 자연어 텍스트 검색: '자연 속 석양', '귀여운 강아지', '도심의 밤'")
    print("   2) 임의의 이미지 분류: classify <이미지경로>")
    print("   3) 유사한 이미지 검색: imgsearch <이미지경로>")
    print("   4) 신규 이미지 추가  : add <이미지경로> [제목]")
    print("   5) 기타 명령어        : list (목록), open <순위> (열기), q (종료)")
    print("=" * 66 + "\n")


def display_results(query: str, results: list):
    """검색 결과를 시각적으로 정돈하여 출력합니다."""
    if not results:
        print("\n❌ 검색 결과가 없습니다.")
        return

    top1 = results[0]

    print("\n" + "━" * 66)
    print(f" 🎯 쿼리: \"{query}\"")
    print("━" * 66)

    # 1. 최우선 매칭 이미지 (1위) 단독 하이라이트
    print(" 🌟 [최우선 추천 이미지 1위]")
    print(f"   ▶ 제  목: {top1.title}")
    print(f"   ▶ 파일명: {top1.filename}")
    print(f"   ▶ 유사도: {top1.similarity:.4f} (일치도 {top1.score_percent:.1f}%)")
    print(f"   ▶ 설  명: {top1.description}")
    print("━" * 66)

    # 2. 상위 3개 순위 요약 테이블
    print(" 📊 [유사도 순위 Top 3 결과]")
    print(f" {'순위':<4} | {'유사도':<9} | {'일치도':<6} | {'이미지 제목 / 파일명'}")
    print(" " + "-" * 62)
    for res in results:
        print(f"  #{res.rank:<3} | {res.similarity:+.4f}   | {res.score_percent:5.1f}% | {res.title} ({res.filename})")
    print("━" * 66)

    # 3. 각 순위별 상세 카드 보기
    print("\n [세부 정보]")
    for res in results:
        print(res.format_card())
    print()


def handle_classify(engine: ImageSearchEngine, target_path: str):
    """임의의 이미지 분류 처리"""
    path = Path(target_path.strip())
    if not path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {path}")
        return

    print(f"\n🏷️ 이미지 분류 분석을 시작합니다: {path.name}...")
    res = engine.classify_image(path)
    print(res.format_summary())


def handle_imgsearch(engine: ImageSearchEngine, target_path: str):
    """임의의 이미지를 통한 유사 이미지 검색 처리"""
    path = Path(target_path.strip())
    if not path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {path}")
        return

    print(f"\n🖼️ 유사 이미지 검색 분석 중: {path.name}...")
    results = engine.search_by_image(path, top_k=3)
    display_results(f"[이미지 쿼리] {path.name}", results)


def handle_add_image(engine: ImageSearchEngine, args_str: str):
    """신규 이미지 보관함 등록 처리"""
    parts = args_str.split(maxsplit=1)
    if not parts:
        print("❌ 사용법: add <이미지파일경로> [제목]")
        return

    file_path = parts[0]
    title = parts[1] if len(parts) > 1 else None

    try:
        item = engine.add_custom_image(file_path, title=title)
        print(f"\n✅ 이미지가 성공적으로 추가 및 인덱싱되었습니다!")
        print(f"  • 파일명: {item.filename}")
        print(f"  • 제  목: {item.title}")
        print(f"  • 설  명: {item.description}")
        print(f"  • 총 색인 수: {len(engine.indexed_items)}개\n")
    except Exception as e:
        print(f"❌ 이미지 추가 실패: {e}")


def run_interactive_cli(engine: ImageSearchEngine):
    """대화형 CLI 루프"""
    print_banner(engine)
    last_results = []

    while True:
        try:
            user_input = input("🔎 입력 (텍스트 검색어 / classify / imgsearch / add / q) > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n프로그램을 종료합니다. 감사합니다!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        # 종료 명령
        if cmd in ("q", "quit", "exit", "종료"):
            print("\n프로그램을 종료합니다. 이용해 주셔서 감사합니다! 👋")
            break

        # 도움말 명령
        if cmd in ("help", "도움말", "?"):
            print("\n[사용 안내]")
            print(" - 자연어 검색: '자연 속 석양', '귀여운 강아지', '도시 야경 불빛'")
            print(" - 이미지 분류: classify <이미지경로> (예: classify search_images/image1_sunset_mountain.bmp)")
            print(" - 유사 이미지: imgsearch <이미지경로> (보관함에서 가장 닮은 이미지 검색)")
            print(" - 이미지 추가: add <이미지경로> [제목] (새 이미지를 보관함에 즉시 등록)")
            print(" - list        : 등록된 모든 이미지 목록과 설명 확인")
            print(" - reindex     : 이미지를 다시 분석하고 캐시를 갱신")
            print(" - open <순위> : 직전 검색 결과의 이미지 파일 열기 (예: open 1)")
            print(" - q           : 프로그램 종료\n")
            continue

        # 임의의 이미지 분류 명령어
        if cmd.startswith("classify "):
            target = user_input[9:].strip()
            handle_classify(engine, target)
            continue

        # 유사 이미지 검색 명령어
        if cmd.startswith("imgsearch "):
            target = user_input[10:].strip()
            handle_imgsearch(engine, target)
            continue

        # 이미지 추가 명령어
        if cmd.startswith("add "):
            target = user_input[4:].strip()
            handle_add_image(engine, target)
            continue

        # 목록 확인 명령
        if cmd in ("list", "목록", "ls"):
            items = engine.get_indexed_items_list()
            print(f"\n📁 [현재 등록된 이미지 총 {len(items)}개]")
            for idx, item in enumerate(items, 1):
                print(f"  {idx}. [{item.title}] ({item.filename})")
                print(f"     설명: {item.description}")
            print()
            continue

        # 재인덱싱 명령
        if cmd in ("reindex", "갱신"):
            print("\n🔄 인덱스를 새로고침합니다...")
            engine.build_index(force_refresh=True)
            continue

        # 이미지 열기 명령 (예: open 1)
        if cmd.startswith("open"):
            parts = cmd.split()
            if len(parts) >= 2 and parts[1].isdigit():
                target_rank = int(parts[1])
                matching = [r for r in last_results if r.rank == target_rank]
                if matching:
                    open_file_in_viewer(matching[0].file_path)
                else:
                    print(f"❌ {target_rank}위 검색 결과를 찾을 수 없습니다. 먼저 검색을 수행해주세요.")
            elif last_results:
                open_file_in_viewer(last_results[0].file_path)
            else:
                print("❌ 열 수 있는 직전 검색 결과가 없습니다.")
            continue

        # 텍스트 검색 실행
        results = engine.search(user_input, top_k=3)
        last_results = results
        display_results(user_input, results)


def run_demo(engine: ImageSearchEngine):
    """과제 요구사항 예시 시나리오 + 신규 이미지 분류 자동 데모 실행"""
    print("\n" + "=" * 66)
    print(" 🎬 과제 요구사항 예시 시나리오 데모 실행")
    print("=" * 66)

    demo_query = "자연 속 석양"
    print(f"\n [사용자의 텍스트 쿼리]: \"{demo_query}\"")
    results = engine.search(demo_query, top_k=3)
    display_results(demo_query, results)

    # 신규 기능 데모: 임의의 이미지 분류 테스트
    print("\n" + "=" * 66)
    print(" 🏷️ [신규 기능 데모] 임의의 이미지 카테고리 자동 분류 테스트")
    print("=" * 66)
    sample_files = [
        "search_images/image1_sunset_mountain.bmp",
        "search_images/image2_cute_puppy.bmp",
        "search_images/image3_night_city.bmp"
    ]
    for sf in sample_files:
        p = Path(sf)
        if p.exists():
            print(f"\n▶ 대상 파일: {p.name}")
            c_res = engine.classify_image(p)
            print(c_res.format_summary())


def main():
    parser = argparse.ArgumentParser(description="AI 텍스트 쿼리 이미지 검색 및 이미지 분류 프로그램")
    parser.add_argument("--query", "-q", type=str, help="즉시 검색할 텍스트 쿼리")
    parser.add_argument("--classify", "-c", type=str, help="분류할 임의의 이미지 파일 경로")
    parser.add_argument("--imgsearch", type=str, help="유사 이미지를 찾을 쿼리 이미지 파일 경로")
    parser.add_argument("--add", type=str, help="보관함에 추가할 이미지 파일 경로")
    parser.add_argument("--top_k", "-k", type=int, default=3, help="반환할 상위 결과 수 (기본: 3)")
    parser.add_argument("--demo", action="store_true", help="요구사항 예시 시나리오 및 분류 자동 데모")
    parser.add_argument("--reindex", action="store_true", help="이미지 메타데이터 캐시 강제 재구축")
    parser.add_argument("--image_dir", type=str, default="search_images", help="이미지 디렉토리 경로")
    args = parser.parse_args()

    # 이미지 파일이 없으면 자동 생성
    img_dir = Path(args.image_dir)
    if not img_dir.exists() or not any(img_dir.iterdir()):
        print(f"[안내] '{args.image_dir}' 디렉토리에 이미지가 없어 샘플 이미지를 자동 생성합니다...")
        from prepare_search_images import create_search_images
        create_search_images(args.image_dir)

    engine = ImageSearchEngine(image_dir=args.image_dir)
    engine.build_index(force_refresh=args.reindex, verbose=True)

    if args.demo:
        run_demo(engine)
    elif args.classify:
        handle_classify(engine, args.classify)
    elif args.imgsearch:
        handle_imgsearch(engine, args.imgsearch)
    elif args.add:
        handle_add_image(engine, args.add)
    elif args.query:
        results = engine.search(args.query, top_k=args.top_k)
        display_results(args.query, results)
    else:
        run_interactive_cli(engine)


if __name__ == "__main__":
    main()
