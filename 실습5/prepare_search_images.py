"""
검색 대상 샘플 이미지 준비 스크립트 (prepare_search_images.py)
=============================================================
과제 요구사항 예시를 충족하는 5가지 테마의 고품질 샘플 이미지를 생성합니다.
1. 산 위로 저무는 아름다운 석양 (Sunset over Mountain)
2. 공원에서 노는 귀여운 강아지 (Cute Puppy in Park)
3. 밤의 번화한 도시 스카이라인 (City Skyline at Night)
4. 눈 덮인 고요한 겨울 숲 (Winter Snow Forest)
5. 에메랄드빛 바다와 휴양지 해변 (Tropical Ocean Beach)

* Pillow(PIL) 설치 시: 고해상도 PNG 파일로 렌더링
* 표준 라이브러리 환경: 완전 호환 24-bit TrueColor BMP 이미지로 렌더링
"""

import math
import os
from pathlib import Path


def generate_bmp_image(filepath: Path, width: int, height: int, draw_fn):
    """표준 라이브러리만으로 24-bit BMP 이미지를 생성합니다."""
    row_padded = (width * 3 + 3) & (~3)
    image_size = row_padded * height
    file_size = 54 + image_size

    # BMP Header (14 bytes) + DIB Header (40 bytes)
    header = bytearray(54)
    header[0:2] = b'BM'
    header[2:6] = file_size.to_bytes(4, 'little')
    header[10:14] = (54).to_bytes(4, 'little')
    header[14:18] = (40).to_bytes(4, 'little')
    header[18:22] = width.to_bytes(4, 'little')
    header[22:26] = height.to_bytes(4, 'little')
    header[26:28] = (1).to_bytes(2, 'little')
    header[28:30] = (24).to_bytes(2, 'little')
    header[34:38] = image_size.to_bytes(4, 'little')

    pixel_data = bytearray(image_size)

    # BMP는 아래에서 위로(bottom-up) 행을 저장합니다.
    for y in range(height):
        # image coordinate: (0,0) is top-left
        img_y = height - 1 - y
        row_offset = y * row_padded
        for x in range(width):
            r, g, b = draw_fn(x, img_y, width, height)
            px = row_offset + x * 3
            pixel_data[px] = b & 0xFF
            pixel_data[px + 1] = g & 0xFF
            pixel_data[px + 2] = r & 0xFF

    with open(filepath, 'wb') as f:
        f.write(header)
        f.write(pixel_data)


# -------------------------------------------------------------
# 테마별 절차적 픽셀 아트 렌더러
# -------------------------------------------------------------
def render_sunset(x: int, y: int, w: int, h: int):
    """산 위로 저무는 석양 렌더러"""
    # 하늘 그라데이션 (진한 자주 -> 주황 -> 황금 노을)
    t = y / (h * 0.7)
    if t <= 1.0:
        r = int(240 * (1 - t * 0.2))
        g = int(80 + 120 * t)
        b = int(40 * (1 - t * 0.5))
    else:
        r, g, b = (220, 160, 60)

    # 태양 (태양 중심: x=w*0.5, y=h*0.48, 반지름 45)
    sun_x, sun_y = w * 0.5, h * 0.48
    dist_sun = math.hypot(x - sun_x, y - sun_y)
    if dist_sun < 45:
        # 태양 중심부
        alpha = dist_sun / 45
        r = int(255 * (1 - alpha) + r * alpha)
        g = int(240 * (1 - alpha) + g * alpha)
        b = int(180 * (1 - alpha) + b * alpha)
    elif dist_sun < 80:
        # 태양 후광 (Glow)
        glow = (80 - dist_sun) / 35 * 0.4
        r = min(255, int(r + 100 * glow))
        g = min(255, int(g + 60 * glow))

    # 먼 산 실루엣
    m1_height = h * 0.55 + 30 * math.sin(x * 0.015) + 20 * math.cos(x * 0.03)
    if y >= m1_height:
        r, g, b = (110, 45, 60)

    # 앞쪽 산봉우리 실루엣
    m2_height = h * 0.68 + 45 * math.sin(x * 0.012 + 1.2) + 25 * math.cos(x * 0.025)
    if y >= m2_height:
        r, g, b = (50, 20, 35)

    return (r, g, b)


def render_puppy_park(x: int, y: int, w: int, h: int):
    """공원에서 뛰노는 강아지 렌더러"""
    # 맑은 하늘 그라데이션 (위: 파랑 -> 지평선: 연파랑)
    if y < h * 0.55:
        t = y / (h * 0.55)
        r = int(100 + 80 * t)
        g = int(180 + 50 * t)
        b = int(245)
        # 구름
        if 40 < y < 90 and (100 < x < 240 or 400 < x < 520):
            r, g, b = (250, 250, 255)
    else:
        # 푸른 잔디밭
        t = (y - h * 0.55) / (h * 0.45)
        r = int(60 - 20 * t)
        g = int(175 - 35 * t)
        b = int(60 - 20 * t)

    # 공원 큰 나무 (우측)
    tree_x, tree_y = w * 0.82, h * 0.45
    dist_tree = math.hypot(x - tree_x, y - tree_y)
    if dist_tree < 85:
        r, g, b = (34, 139, 34)
    # 나무 줄기
    if abs(x - tree_x) < 14 and h * 0.45 <= y <= h * 0.7:
        r, g, b = (101, 67, 33)

    # 귀여운 강아지 몸체 (중앙-좌측: x=w*0.4, y=h*0.68)
    dog_x, dog_y = w * 0.4, h * 0.68
    # 강아지 몸통 (타원)
    if ((x - dog_x) / 38)**2 + ((y - dog_y) / 24)**2 <= 1.0:
        r, g, b = (235, 175, 105)  # 황금빛 털
    # 강아지 머리
    head_x, head_y = dog_x + 35, dog_y - 18
    if ((x - head_x) / 22)**2 + ((y - head_y) / 20)**2 <= 1.0:
        r, g, b = (235, 175, 105)
    # 강아지 귀
    ear_x, ear_y = head_x - 8, head_y - 18
    if math.hypot(x - ear_x, y - ear_y) <= 10:
        r, g, b = (180, 115, 60)
    # 강아지 눈 & 코
    if math.hypot(x - (head_x + 8), y - (head_y - 2)) <= 3:
        r, g, b = (20, 20, 20)  # 눈
    if math.hypot(x - (head_x + 18), y - head_y) <= 4:
        r, g, b = (30, 20, 20)  # 코
    # 빨간 장난감 공
    ball_x, ball_y = dog_x + 80, dog_y + 10
    if math.hypot(x - ball_x, y - ball_y) <= 12:
        r, g, b = (230, 40, 40)

    return (r, g, b)


def render_city_night(x: int, y: int, w: int, h: int):
    """밤의 번화한 도시 스카이라인 렌더러"""
    # 짙푸른 밤하늘
    t = y / h
    r = int(10 + 20 * t)
    g = int(12 + 25 * t)
    b = int(35 + 45 * t)

    # 밤하늘 별
    if (x * 37 + y * 73) % 499 == 7 and y < h * 0.4:
        r, g, b = (240, 240, 255)

    # 달 (초승달/만월)
    moon_x, moon_y = w * 0.18, h * 0.18
    if math.hypot(x - moon_x, y - moon_y) <= 22:
        r, g, b = (255, 250, 210)

    # 고층 빌딩 실루엣 (사각 블록들)
    buildings = [
        (0.00, 0.12, 0.45),
        (0.10, 0.22, 0.32),
        (0.20, 0.34, 0.50),
        (0.32, 0.46, 0.28),
        (0.44, 0.58, 0.40),
        (0.56, 0.70, 0.30),
        (0.68, 0.82, 0.52),
        (0.80, 0.92, 0.38),
        (0.90, 1.00, 0.46),
    ]

    for start_f, end_f, top_f in buildings:
        bx1, bx2 = int(w * start_f), int(w * end_f)
        by = int(h * top_f)
        if bx1 <= x <= bx2 and y >= by:
            # 빌딩 기본 색상
            r, g, b = (22, 28, 48)

            # 창문 불빛 격자 (노랑, 주황, 청록 네온 불빛)
            grid_x = (x - bx1) % 18
            grid_y = (y - by) % 22
            window_seed = (x // 18 * 17 + y // 22 * 31) % 11
            if 4 <= grid_x <= 13 and 5 <= grid_y <= 16 and window_seed > 3:
                if window_seed % 3 == 0:
                    r, g, b = (255, 225, 120)  # 따뜻한 백열등
                elif window_seed % 3 == 1:
                    r, g, b = (255, 180, 80)   # 주황빛
                else:
                    r, g, b = (120, 230, 255)  # 네온 블루

    return (r, g, b)


def render_winter_forest(x: int, y: int, w: int, h: int):
    """눈 덮인 고요한 겨울 숲 렌더러"""
    # 은회색 차분한 겨울 하늘
    t = y / (h * 0.6)
    if y < h * 0.6:
        r = int(190 + 25 * t)
        g = int(205 + 20 * t)
        b = int(225 + 15 * t)
    else:
        # 눈 덮인 설원
        t2 = (y - h * 0.6) / (h * 0.4)
        r = int(240 - 20 * t2)
        g = int(245 - 15 * t2)
        b = int(255 - 10 * t2)

    # 침엽수 나무들 (삼각형 눈 덮인 트리)
    trees = [
        (int(w * 0.15), int(h * 0.55), 70),
        (int(w * 0.35), int(h * 0.62), 90),
        (int(w * 0.60), int(h * 0.58), 80),
        (int(w * 0.85), int(h * 0.65), 100),
    ]

    for tx, ty, tree_h in trees:
        dx = abs(x - tx)
        dy = y - (ty - tree_h)
        if 0 <= dy <= tree_h and dx <= (dy / tree_h) * (tree_h * 0.4):
            # 트리 안쪽
            if (x + y) % 12 < 4:
                r, g, b = (245, 250, 255)  # 나뭇가지 위 쌓인 눈
            else:
                r, g, b = (28, 65, 45)     # 짙은 상록수 초록

    return (r, g, b)


def render_tropical_beach(x: int, y: int, w: int, h: int):
    """에메랄드빛 바다와 휴양지 해변 렌더러"""
    # 화창한 여름 하늘 (0.0 ~ 0.45)
    if y < h * 0.45:
        t = y / (h * 0.45)
        r = int(90 + 90 * t)
        g = int(180 + 55 * t)
        b = int(250)
    # 에메랄드빛 바다 (0.45 ~ 0.72)
    elif y < h * 0.72:
        t = (y - h * 0.45) / (h * 0.27)
        r = int(20 + 30 * t)
        g = int(170 + 35 * t)
        b = int(190 - 20 * t)
        # 흰 파도 거품
        if abs(y - int(h * 0.71)) <= 3:
            r, g, b = (250, 255, 255)
    # 백사장 (0.72 ~ 1.0)
    else:
        t = (y - h * 0.72) / (h * 0.28)
        r = int(240 - 20 * t)
        g = int(225 - 25 * t)
        b = int(185 - 30 * t)

    # 야자수 (우측 가장자리)
    palm_x = w * 0.88
    if abs(x - (palm_x + 15 * math.sin(y * 0.02))) < 8 and y > h * 0.35:
        r, g, b = (120, 85, 45)  # 줄기

    # 야자수 잎
    if math.hypot(x - palm_x, y - (h * 0.35)) < 65 and y < h * 0.42:
        r, g, b = (35, 140, 50)

    return (r, g, b)


# -------------------------------------------------------------
# 전체 이미지 세트 정의 및 생성기
# -------------------------------------------------------------
IMAGE_DATASET = [
    {
        "id": "image1",
        "filename": "image1_sunset_mountain.bmp",
        "title": "산 위로 저무는 아름다운 석양",
        "renderer": render_sunset,
        "default_description": (
            "산봉우리 능선 너머로 붉고 황금빛으로 물든 노을이 펼쳐진 아름다운 일몰 풍경. "
            "따뜻한 주황빛과 보랏빛 하늘이 어우러져 고요하고 웅장한 자연 속 석양의 감동을 선사합니다."
        ),
        "tags": ["석양", "일몰", "산", "노을", "자연", "하늘", "황금빛", "풍경"]
    },
    {
        "id": "image2",
        "filename": "image2_cute_puppy.bmp",
        "title": "공원에서 노는 귀여운 강아지",
        "renderer": render_puppy_park,
        "default_description": (
            "푸른 잔디가 싱그럽게 펼쳐진 야외 공원에서 빨간 공을 곁에 두고 신나게 뛰어노는 귀여운 강아지. "
            "따스한 햇살과 초록 나무 아래에서 활기차고 사랑스러운 반려동물의 행복한 모습을 담고 있습니다."
        ),
        "tags": ["강아지", "개", "동물", "공원", "잔디", "반려동물", "귀여운", "공놀이"]
    },
    {
        "id": "image3",
        "filename": "image3_night_city.bmp",
        "title": "밤의 번화한 도시 스카이라인",
        "renderer": render_city_night,
        "default_description": (
            "깊은 밤하늘 아래 형형색색의 네온사인과 화려한 조명으로 찬란하게 빛나는 고층 빌딩 스카이라인. "
            "야경이 아름다운 도심의 세련되고 번화한 도시 풍경을 역동적으로 보여줍니다."
        ),
        "tags": ["도시", "야경", "스카이라인", "빌딩", "밤", "네온사인", "도심", "야간"]
    },
    {
        "id": "image4",
        "filename": "image4_winter_forest.bmp",
        "title": "눈 덮인 고요한 겨울 숲",
        "renderer": render_winter_forest,
        "default_description": (
            "순백의 흰 눈이 소복이 쌓인 울창한 침엽수림과 눈 덮인 겨울 산림의 고요한 설경. "
            "차분하고 서정적인 겨울 자연의 정취와 맑고 깨끗한 계절감을 느낄 수 있습니다."
        ),
        "tags": ["겨울", "눈", "설경", "숲", "침엽수", "나무", "자연", "하얀눈"]
    },
    {
        "id": "image5",
        "filename": "image5_tropical_beach.bmp",
        "title": "에메랄드빛 바다와 휴양지 해변",
        "renderer": render_tropical_beach,
        "default_description": (
            "투명하고 맑은 에메랄드빛 바다와 부드러운 백사장, 시원한 야자수가 어우러진 여름 휴양지 해변. "
            "푸른 파도와 이국적인 해안선이 어우러져 평화롭고 청량한 자연 휴양의 풍경을 전합니다."
        ),
        "tags": ["바다", "해변", "휴양지", "백사장", "야자수", "파도", "에메랄드", "여름"]
    }
]


def create_search_images(target_dir: str = "search_images", width: int = 600, height: int = 400):
    """지정된 디렉토리에 테스트용 이미지들을 생성합니다."""
    out_path = Path(target_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"============================================================")
    print(f" 🎨 검색용 고품질 샘플 이미지 생성 시작 ({target_dir}/)")
    print(f"============================================================")

    generated_files = []
    for item in IMAGE_DATASET:
        filepath = out_path / item["filename"]
        print(f"  ▶ 생성 중: {item['filename']} - '{item['title']}'...")
        generate_bmp_image(filepath, width, height, item["renderer"])
        generated_files.append(filepath)
        print(f"    ✓ 완료: {filepath} ({width}x{height} 24-bit TrueColor)")

    print(f"\n총 {len(generated_files)}개의 샘플 이미지가 성공적으로 준비되었습니다!\n")
    return generated_files


if __name__ == "__main__":
    create_search_images()
