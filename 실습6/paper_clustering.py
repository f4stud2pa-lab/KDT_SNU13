#!/usr/bin/env python3
"""
논문 유사도 기반 군집화 CLI 메인 프로그램 (paper_clustering.py)
=============================================================
PDF 연구 논문들을 읽고, 벡터 임베딩으로 변환한 뒤 의미적 유사도를 기반으로
K-Means 클러스터링 및 PCA 2D/3D 시각화를 수행합니다.

사용법:
    # 기본 실행 (대화형 안내 모드 또는 기본 K=4 적용)
    python paper_clustering.py

    # 클러스터 개수 직접 지정 (예: 3개 또는 4개)
    python paper_clustering.py -k 4

    # 특정 폴더 및 시각화 즉시 열기
    python paper_clustering.py --dir papers -k 4 --open

    # 임베딩 모드 지정 (auto / tfidf / openai)
    python paper_clustering.py -k 4 --mode auto
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from paper_cluster_engine import PaperClusteringEngine, PaperDocument
from visualizer import PaperVisualizer


def open_file_in_viewer(filepath: str):
    """운영체제 기본 뷰어 또는 브라우저로 파일을 엽니다."""
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
        print(f"👁️ 뷰어로 열었습니다: {path.name}")
    except Exception as e:
        print(f"⚠️ 파일 열기 실패: {e}")


def print_banner(papers_dir: str, num_papers: int, backend: str):
    """프로그램 시작 배너를 출력합니다."""
    print("\n" + "=" * 76)
    print(" 📚 논문 유사도 기반 의미론적 군집화 시스템 (Paper Semantic Clustering)")
    print("=" * 76)
    print(f" • 대상 디렉토리  : {papers_dir}")
    print(f" • 발견된 논문 수 : {num_papers} 편")
    print(f" • 임베딩 엔진    : {backend}")
    print(" • 지원 기능      : PDF 텍스트 추출, 벡터 임베딩, K-Means 군집화, 2D/3D PCA 시각화")
    print("=" * 76 + "\n")


def display_clustering_results(engine: PaperClusteringEngine, k: int):
    """클러스터링 결과를 터미널에 구조화하여 출력합니다."""
    print("\n" + "#" * 76)
    print(f" 🎯 [군집화 결과 요약] 총 {len(engine.papers)}편의 논문을 {k}개 클러스터로 분류 완료")
    print("#" * 76)

    for c_id in range(k):
        summary = engine.cluster_summary.get(c_id, {})
        dominant_cat = summary.get("dominant_category", f"클러스터 {c_id}")
        count = summary.get("count", 0)
        keywords = summary.get("top_keywords", [])
        kw_str = ", ".join(keywords[:5]) if keywords else "키워드 없음"

        print(f"\n┌──────────────────────────────────────────────────────────────────────────")
        print(f"│ 🏷️  [클러스터 #{c_id}] {dominant_cat} ({count}편 포함)")
        print(f"│ 🔑 핵심 대표 키워드: {kw_str}")
        print(f"├──────────────────────────────────────────────────────────────────────────")

        member_papers = [p for p in engine.papers if p.cluster_id == c_id]
        for p_idx, p in enumerate(member_papers, start=1):
            print(f"│  [{p_idx}] 📄 제목: {p.title}")
            print(f"│       📁 파일: {p.filename}")
            if p.authors:
                print(f"│       ✍️  저자: {p.authors}")
            if p.abstract:
                # 80자씩 2줄 정도 출력
                clean_abs = p.abstract.replace("\n", " ").strip()
                preview = clean_abs[:130] + "..." if len(clean_abs) > 130 else clean_abs
                print(f"│       💡 요약: {preview}")
            if p.pca_2d:
                print(f"│       📍 2D 좌표: PC1={p.pca_2d[0]:.3f}, PC2={p.pca_2d[1]:.3f}")
            if p_idx < len(member_papers):
                print(f"│       {'-' * 66}")
        print(f"└──────────────────────────────────────────────────────────────────────────")


def display_similarity_sample(engine: PaperClusteringEngine):
    """논문 간 코사인 유사도 상위 및 클러스터 간 유사도 분석 요약 출력"""
    sim_matrix = engine.compute_similarity_matrix()
    n = len(engine.papers)

    print("\n" + "=" * 76)
    print(" 📊 [유사도 분석] 각 논문별 가장 의미적으로 유사한 Top-1 논문 매칭")
    print("=" * 76)

    for i in range(n):
        p_i = engine.papers[i]
        # 자기 자신 제외하고 최대 유사도 찾기
        best_sim = -1.0
        best_idx = -1
        for j in range(n):
            if i != j:
                if sim_matrix[i, j] > best_sim:
                    best_sim = sim_matrix[i, j]
                    best_idx = j

        if best_idx != -1:
            p_j = engine.papers[best_idx]
            match_status = "✅ 동일 클러스터" if p_i.cluster_id == p_j.cluster_id else "⚠️ 타 클러스터"
            print(f" • [논문 {i+1:02d}] {p_i.filename[:30]:<30}")
            print(f"   ↳ 가장 유사한 논문: {p_j.filename[:30]} (유사도: {best_sim:.4f}) [{match_status}]")

    print("=" * 76)


def main():
    parser = argparse.ArgumentParser(
        description="연구 논문 PDF 의미론적 유사도 기반 K-Means 군집화 및 차원 축소 시각화 프로그램"
    )
    parser.add_argument(
        "--dir", "-d",
        type=str,
        default="papers",
        help="PDF 논문 파일들이 저장된 디렉토리 경로 (기본값: papers)"
    )
    parser.add_argument(
        "--clusters", "-k",
        type=int,
        default=None,
        help="생성할 클러스터의 개수 (지정하지 않으면 대화형 프롬프트 또는 추천값 적용)"
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["auto", "tfidf", "openai"],
        default="auto",
        help="텍스트 임베딩 생성 방식 (auto: API 키 유무에 따라 자동 선택, tfidf: 로컬 TF-IDF, openai: OpenAI API)"
    )
    parser.add_argument(
        "--vis",
        type=str,
        choices=["2d", "3d", "html", "all", "none"],
        default="all",
        help="시각화 출력 포맷 (2d: 2D PNG, 3d: 3D PNG, html: 인터랙티브 웹 대시보드, all: 모두 생성)"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="시각화 생성 완료 후 생성된 이미지 또는 HTML을 기본 뷰어로 자동 오픈"
    )

    args = parser.parse_args()

    # 작업 디렉토리 기준 경로 해석
    script_dir = Path(__file__).parent.resolve()
    papers_dir = Path(args.dir)
    if not papers_dir.is_absolute():
        papers_dir = script_dir / args.dir

    # 샘플 파일이 없으면 자동 생성 안내 및 생성
    if not papers_dir.exists() or not list(papers_dir.glob("*.pdf")):
        print(f"⚠️ 디렉토리에 PDF 파일이 없습니다: {papers_dir}")
        print("💡 샘플 논문 PDF 10편을 자동으로 생성합니다...")
        from prepare_sample_papers import create_sample_papers
        create_sample_papers(str(papers_dir))

    # 엔진 초기화 및 논문 로드
    engine = PaperClusteringEngine(embedding_mode=args.mode)
    try:
        papers = engine.load_papers(papers_dir)
    except Exception as e:
        print(f"❌ 논문 로드 실패: {e}")
        sys.exit(1)

    print_banner(str(papers_dir), len(papers), engine.embedding_engine.active_backend.upper())

    # K값 결정 (사용자 입력 또는 추천)
    k = args.clusters
    if k is None:
        recommended_k = engine.suggest_optimal_k(max_k=min(6, len(papers) - 1))
        print(f"💡 시스템 분석 결과 권장 클러스터 개수: K={recommended_k}")
        try:
            user_input = input(f"👉 원하는 클러스터 개수 K를 입력하세요 (기본값 엔터: {recommended_k}): ").strip()
            if user_input.isdigit() and int(user_input) > 0:
                k = int(user_input)
            else:
                k = recommended_k
        except (KeyboardInterrupt, EOFError):
            print(f"\n기본값 K={recommended_k}로 진행합니다.")
            k = recommended_k

    if k > len(papers):
        print(f"⚠️ 지정한 K({k})가 논문 수({len(papers)})보다 커서 K={len(papers)}로 자동 조정합니다.")
        k = len(papers)

    print(f"\n🚀 K={k}개 클러스터로 군집화 알고리즘을 실행합니다...")

    # 군집화 실행
    engine.perform_clustering(k=k)

    # 1. 터미널 결과 출력
    display_clustering_results(engine, k)

    # 2. 유사도 매칭 요약 출력
    display_similarity_sample(engine)

    # 3. 시각화 생성
    out_files = []
    if args.vis in ("2d", "all"):
        out_2d = script_dir / "cluster_2d.png"
        p2d = PaperVisualizer.plot_clusters_2d(engine.papers, engine.cluster_summary, str(out_2d))
        if p2d:
            print(f"\n🖼️ 2D PCA 산점도 저장 완료: {p2d}")
            out_files.append(p2d)

    if args.vis in ("3d", "all"):
        out_3d = script_dir / "cluster_3d.png"
        p3d = PaperVisualizer.plot_clusters_3d(engine.papers, engine.cluster_summary, str(out_3d))
        if p3d:
            print(f"🌐 3D PCA 산점도 저장 완료: {p3d}")
            out_files.append(p3d)

    if args.vis in ("html", "all"):
        out_html = script_dir / "cluster_interactive.html"
        phtml = PaperVisualizer.generate_interactive_html(
            engine.papers,
            engine.cluster_summary,
            engine.similarity_matrix,
            str(out_html)
        )
        print(f"✨ 인터랙티브 웹 리포트 저장 완료: {phtml}")
        out_files.append(phtml)

    # 결과 자동 열기
    if args.open and out_files:
        # HTML 또는 2D 이미지 열기
        target_to_open = out_files[-1]  # 보통 HTML
        print(f"\n🚀 결과 파일을 기본 뷰어로 실행합니다: {Path(target_to_open).name}")
        open_file_in_viewer(target_to_open)

    print("\n✅ 모든 군집화 및 시각화 프로세스가 성공적으로 완료되었습니다.\n")


if __name__ == "__main__":
    main()
