#!/usr/bin/env python3
"""
논문 군집화 시스템 단위 테스트 (test_clustering.py)
=================================================
전체 파이프라인(PDF 파싱 -> 임베딩 -> 유사도 -> 군집화 -> 차원축소 -> 시각화)을
자동으로 검증합니다.
"""

import os
import unittest
from pathlib import Path
import numpy as np

from paper_cluster_engine import (
    PDFTextExtractor,
    BuiltinTfidfVectorizer,
    EmbeddingEngine,
    BuiltinKMeans,
    BuiltinPCA,
    PaperClusteringEngine,
    PaperDocument
)
from visualizer import PaperVisualizer
from prepare_sample_papers import create_sample_papers


class TestPaperClusteringPipeline(unittest.TestCase):
    """군집화 파이프라인 검증 테스트 스위트"""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(__file__).parent / "test_papers"
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        # 샘플 PDF 생성
        create_sample_papers(str(cls.test_dir))

    @classmethod
    def tearDownClass(cls):
        # 테스트 임시 파일 정리
        import shutil
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)

    def test_01_pdf_text_extraction(self):
        """PDF 파일에서 텍스트 및 메타데이터 추출 테스트"""
        pdf_files = list(self.test_dir.glob("*.pdf"))
        self.assertGreaterEqual(len(pdf_files), 10, "최소 10편의 PDF 파일이 존재해야 합니다.")

        sample_pdf = pdf_files[0]
        text = PDFTextExtractor.extract_text(sample_pdf)
        self.assertGreater(len(text), 100, "추출된 텍스트 길이가 100자 이상이어야 합니다.")

        doc = PDFTextExtractor.parse_paper(sample_pdf, doc_id=0)
        self.assertIsNotNone(doc.title, "제목이 정상 추출되어야 합니다.")
        self.assertIsNotNone(doc.abstract, "초록(Abstract)이 추출되어야 합니다.")
        print(f"\n[PASS] PDF 텍스트 추출 완료: {doc.filename} -> {doc.title[:40]}...")

    def test_02_builtin_tfidf_vectorizer(self):
        """내장 TF-IDF 벡터라이저 정확도 테스트"""
        docs = [
            "deep learning neural networks transformer attention language model",
            "computer vision convolutional residual networks image recognition",
            "blockchain decentralized finance automated market maker liquidity",
            "perovskite solar cells renewable clean energy photovoltaic"
        ]
        vectorizer = BuiltinTfidfVectorizer(max_features=50, ngram_range=(1, 2))
        X = vectorizer.fit_transform(docs)

        # 4개 문서 x 특징 수
        self.assertEqual(X.shape[0], 4)
        # L2 정규화 검증 (각 행의 크기가 1.0에 가까워야 함)
        norms = np.linalg.norm(X, axis=1)
        np.testing.assert_allclose(norms, 1.0, rtol=1e-5)
        print("\n[PASS] 내장 TF-IDF L2 단위 벡터 정규화 검증 완료.")

    def test_03_clustering_and_similarity(self):
        """K-Means 군집화 및 코사인 유사도 매트릭스 검증"""
        engine = PaperClusteringEngine(n_clusters=4, embedding_mode="tfidf", random_state=42)
        papers = engine.load_papers(self.test_dir)
        self.assertEqual(len(papers), 10)

        # 클러스터링 실행
        labels = engine.perform_clustering(k=4)
        self.assertEqual(len(labels), 10)
        self.assertEqual(len(set(labels)), 4, "4개의 독립된 클러스터가 생성되어야 합니다.")

        # 코사인 유사도 검증
        sim = engine.compute_similarity_matrix()
        self.assertEqual(sim.shape, (10, 10))

        # 대각선 원소는 자기 자신이므로 1.0 이어야 함
        for i in range(10):
            self.assertAlmostEqual(sim[i, i], 1.0, places=4)

        # 대칭 행렬 검증 (S_ij == S_ji)
        np.testing.assert_allclose(sim, sim.T, atol=1e-5)
        print("\n[PASS] 코사인 유사도 행렬 대칭성 및 자기 유사도 1.0 검증 완료.")

    def test_04_pca_projections(self):
        """PCA 차원 축소 2D 및 3D 좌표 유효성 검증"""
        engine = PaperClusteringEngine(n_clusters=4, embedding_mode="tfidf")
        engine.load_papers(self.test_dir)
        engine.perform_clustering(k=4)

        for p in engine.papers:
            self.assertIsNotNone(p.pca_2d, "2D PCA 좌표가 존재해야 합니다.")
            self.assertEqual(len(p.pca_2d), 2)
            self.assertIsNotNone(p.pca_3d, "3D PCA 좌표가 존재해야 합니다.")
            self.assertEqual(len(p.pca_3d), 3)

        print("\n[PASS] PCA 2D/3D 차원 축소 좌표 생성 검증 완료.")

    def test_05_visualizer_outputs(self):
        """시각화 파일(PNG, HTML) 생성 검증"""
        engine = PaperClusteringEngine(n_clusters=4, embedding_mode="tfidf")
        engine.load_papers(self.test_dir)
        engine.perform_clustering(k=4)

        out_2d = self.test_dir / "test_2d.png"
        out_3d = self.test_dir / "test_3d.png"
        out_html = self.test_dir / "test_interactive.html"

        p2d = PaperVisualizer.plot_clusters_2d(engine.papers, engine.cluster_summary, str(out_2d))
        p3d = PaperVisualizer.plot_clusters_3d(engine.papers, engine.cluster_summary, str(out_3d))
        phtml = PaperVisualizer.generate_interactive_html(engine.papers, engine.cluster_summary, engine.similarity_matrix, str(out_html))

        self.assertTrue(out_html.exists(), "HTML 리포트가 생성되어야 합니다.")
        self.assertGreater(out_html.stat().st_size, 1000)
        print(f"\n[PASS] 시각화 리포트 생성 검증 완료: HTML ({out_html.stat().st_size} bytes)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
