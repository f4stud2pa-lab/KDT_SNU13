"""
이미지 검색 및 분류 시스템 단위 테스트 및 시나리오 검증 스크립 (test_image_search.py)
=====================================================================================
과제 요구사항 및 핵심 알고리즘, 신규 확장 기능(임의의 이미지 분류, 유사 이미지 검색, 신규 이미지 등록)이
완벽하게 작동하는지 자동으로 검증합니다.
"""

import math
import os
import shutil
import unittest
from pathlib import Path

from image_search_engine import (
    CosineSimilarityCalculator,
    ImageSearchEngine,
    SemanticFallbackEmbedder,
)
from prepare_search_images import create_search_images


class TestCosineSimilarity(unittest.TestCase):
    """코사인 유사도 수학적 정확성 검증"""

    def test_identical_vectors(self):
        vec = [0.3, 0.4, 0.5]
        sim = CosineSimilarityCalculator.calculate(vec, vec)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_orthogonal_vectors(self):
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]
        sim = CosineSimilarityCalculator.calculate(vec_a, vec_b)
        self.assertAlmostEqual(sim, 0.0, places=5)

    def test_opposite_vectors(self):
        vec_a = [1.0, 2.0, 3.0]
        vec_b = [-1.0, -2.0, -3.0]
        sim = CosineSimilarityCalculator.calculate(vec_a, vec_b)
        self.assertAlmostEqual(sim, -1.0, places=5)

    def test_zero_vector_handling(self):
        vec_a = [0.0, 0.0, 0.0]
        vec_b = [1.0, 2.0, 3.0]
        sim = CosineSimilarityCalculator.calculate(vec_a, vec_b)
        self.assertEqual(sim, 0.0)


class TestImageSearchAndClassificationEngine(unittest.TestCase):
    """이미지 검색 엔진 통합 테스트 및 시나리오 검증"""

    @classmethod
    def setUpClass(cls):
        cls.test_img_dir = "test_search_images"
        cls.test_cache = "test_cache.json"
        create_search_images(cls.test_img_dir, width=100, height=100)
        cls.engine = ImageSearchEngine(
            image_dir=cls.test_img_dir,
            cache_file=cls.test_cache
        )
        cls.engine.build_index(force_refresh=True, verbose=False)

    @classmethod
    def tearDownClass(cls):
        if Path(cls.test_cache).exists():
            os.remove(cls.test_cache)
        test_dir = Path(cls.test_img_dir)
        if test_dir.exists():
            for f in test_dir.iterdir():
                f.unlink()
            test_dir.rmdir()

    def test_01_indexing_count(self):
        """총 5개의 이미지가 정상적으로 인덱싱되었는지 확인"""
        self.assertEqual(len(self.engine.indexed_items), 5)

    def test_02_user_requirement_scenario_sunset(self):
        """
        [과제 핵심 요구사항 예시 검증]
        쿼리: '자연 속 석양'
        출력: 1위 결과가 '산 위로 저무는 아름다운 석양'이어야 함
        """
        query = "자연 속 석양"
        results = self.engine.search(query, top_k=3)

        self.assertGreaterEqual(len(results), 1)
        top1 = results[0]

        self.assertIn("sunset", top1.filename.lower())
        self.assertIn("석양", top1.title)
        self.assertGreater(top1.similarity, 0.5)

        self.assertEqual(len(results), 3)
        self.assertGreaterEqual(results[0].similarity, results[1].similarity)
        self.assertGreaterEqual(results[1].similarity, results[2].similarity)

    def test_03_scenario_puppy(self):
        """쿼리 '공원에서 노는 귀여운 강아지' 검증"""
        query = "공원에서 노는 귀여운 강아지"
        results = self.engine.search(query, top_k=3)
        self.assertIn("puppy", results[0].filename.lower())

    def test_04_scenario_night_city(self):
        """쿼리 '밤의 번화한 도시 스카이라인' 검증"""
        query = "밤의 번화한 도시 스카이라인"
        results = self.engine.search(query, top_k=3)
        self.assertIn("city", results[0].filename.lower())

    def test_05_scenario_winter_forest(self):
        """쿼리 '눈 덮인 고요한 겨울 숲' 검증"""
        query = "눈 덮인 고요한 겨울 숲"
        results = self.engine.search(query, top_k=3)
        self.assertIn("winter", results[0].filename.lower())

    def test_06_scenario_tropical_beach(self):
        """쿼리 '에메랄드빛 바다와 휴양지 해변' 검증"""
        query = "에메랄드빛 바다와 휴양지 해변"
        results = self.engine.search(query, top_k=3)
        self.assertIn("beach", results[0].filename.lower())

    # ---------------------------------------------------------
    # [신규 기능 검증] 임의의 이미지 분류 (Classification)
    # ---------------------------------------------------------
    def test_07_classify_sunset_image(self):
        """석양 이미지가 '자연 및 풍경' 카테고리로 올바르게 분류되는지 검증"""
        target = Path(self.test_img_dir) / "image1_sunset_mountain.bmp"
        c_res = self.engine.classify_image(target)
        self.assertIn("자연", c_res.predicted_category)
        self.assertGreater(c_res.similarity_score, 0.5)

    def test_08_classify_puppy_image(self):
        """강아지 이미지가 '동물 및 반려동물' 카테고리로 올바르게 분류되는지 검증"""
        target = Path(self.test_img_dir) / "image2_cute_puppy.bmp"
        c_res = self.engine.classify_image(target)
        self.assertIn("동물", c_res.predicted_category)
        self.assertGreater(c_res.similarity_score, 0.4)

    def test_09_classify_night_city_image(self):
        """도시 야경 이미지가 '도시 및 건축' 카테고리로 올바르게 분류되는지 검증"""
        target = Path(self.test_img_dir) / "image3_night_city.bmp"
        c_res = self.engine.classify_image(target)
        self.assertIn("도시", c_res.predicted_category)
        self.assertGreater(c_res.similarity_score, 0.6)

    # ---------------------------------------------------------
    # [신규 기능 검증] 이미지-to-이미지 유사도 역검색
    # ---------------------------------------------------------
    def test_10_search_by_image(self):
        """이미지를 쿼리로 주었을 때 자기 자신 이미지가 1위로 나오는지 검증"""
        target = Path(self.test_img_dir) / "image1_sunset_mountain.bmp"
        results = self.engine.search_by_image(target, top_k=3)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].filename, "image1_sunset_mountain.bmp")


class TestImageDynamicIngestion(unittest.TestCase):
    """신규 이미지 보관함 동적 추가 테스트 (격리된 환경)"""

    @classmethod
    def setUpClass(cls):
        cls.test_ingest_dir = "test_ingest_images"
        cls.test_cache = "test_ingest_cache.json"
        create_search_images(cls.test_ingest_dir, width=80, height=80)
        cls.engine = ImageSearchEngine(
            image_dir=cls.test_ingest_dir,
            cache_file=cls.test_cache
        )
        cls.engine.build_index(force_refresh=True, verbose=False)

    @classmethod
    def tearDownClass(cls):
        if Path(cls.test_cache).exists():
            os.remove(cls.test_cache)
        test_dir = Path(cls.test_ingest_dir)
        if test_dir.exists():
            for f in test_dir.iterdir():
                f.unlink()
            test_dir.rmdir()

    def test_add_custom_image(self):
        """새로운 임의의 이미지를 추가했을 때 인덱스가 갱신되고 즉시 검색되는지 검증"""
        initial_count = len(self.engine.indexed_items)
        sample_path = Path(self.test_ingest_dir) / "image1_sunset_mountain.bmp"

        new_test_path = Path(self.test_ingest_dir) / "custom_test_sunset.bmp"
        shutil.copy2(sample_path, new_test_path)

        added = self.engine.add_custom_image(new_test_path, title="사용자 추가 노을 이미지")
        self.assertEqual(len(self.engine.indexed_items), initial_count + 1)
        self.assertEqual(added.title, "사용자 추가 노을 이미지")

        results = self.engine.search("노을 이미지", top_k=5)
        found_names = [r.filename for r in results]
        self.assertIn("custom_test_sunset.bmp", found_names)


if __name__ == "__main__":
    unittest.main()
