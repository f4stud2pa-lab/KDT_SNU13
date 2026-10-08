"""
테스트용 4컷 예제 이미지 생성 스크립트
과제 요구사항 예시를 기반으로 4장의 샘플 카드 이미지를 생성합니다:
  - sample_images/scene1_walk.png : 그림 1 (강아지가 공원을 걷는 모습)
  - sample_images/scene2_rest.png : 그림 2 (강아지가 나무 아래에서 쉬는 모습)
  - sample_images/scene3_fetch.png : 그림 3 (강아지가 공을 물어오는 모습)
  - sample_images/scene4_home.png : 그림 4 (강아지가 주인과 함께 집으로 돌아가는 모습)
"""

import os
from pathlib import Path


def create_samples():
    output_dir = Path("sample_images")
    output_dir.mkdir(exist_ok=True)

    scenes = [
        {
            "filename": "scene1_walk.png",
            "title": "[그림 1] 산책의 시작",
            "desc": "강아지가 푸른 공원 산책로를\n주인과 함께 걷는 모습",
            "bg_color": (210, 240, 215),  # 연한 풀빛
            "accent_color": (34, 139, 34),
        },
        {
            "filename": "scene2_rest.png",
            "title": "[그림 2] 나무 그늘 아래 쉼",
            "desc": "시원한 큰 나무 그늘 아래에서\n편안하게 쉬고 있는 강아지",
            "bg_color": (210, 230, 250),  # 연한 하늘빛
            "accent_color": (30, 100, 200),
        },
        {
            "filename": "scene3_fetch.png",
            "title": "[그림 3] 신나는 공놀이",
            "desc": "풀숲에서 빨간 공을 발견하고\n신나게 물어오는 강아지",
            "bg_color": (255, 235, 205),  # 연한 노랑/살구
            "accent_color": (220, 80, 50),
        },
        {
            "filename": "scene4_home.png",
            "title": "[그림 4] 행복한 귀갓길",
            "desc": "노을빛 아래에서 주인과 함께\n나란히 집으로 돌아가는 모습",
            "bg_color": (255, 220, 210),  # 노을빛
            "accent_color": (200, 70, 70),
        },
    ]

    try:
        from PIL import Image, ImageDraw, ImageFont

        print("[안내] Pillow(PIL)를 사용하여 고품질 샘플 이미지를 생성합니다...")
        for s in scenes:
            filepath = output_dir / s["filename"]
            # 600x400 크기의 이미지 생성
            img = Image.new("RGB", (600, 400), color=s["bg_color"])
            draw = ImageDraw.Draw(img)

            # 테두리 및 장식 박스
            draw.rectangle([15, 15, 585, 385], outline=s["accent_color"], width=4)
            draw.rectangle([30, 30, 570, 100], fill=s["accent_color"])

            # 텍스트 그리기 (기본 폰트 사용)
            draw.text((45, 50), s["title"], fill=(255, 255, 255))
            draw.text((50, 150), s["desc"], fill=(40, 40, 40))
            draw.text((50, 280), f"아이콘/상징: {s['symbol']}", fill=(80, 80, 80))

            img.save(filepath, "PNG")
            print(f"  ✓ 생성 완료: {filepath}")

    except ImportError:
        print("[안내] Pillow가 감지되지 않아 표준 라이브러리로 호환 BMP 이미지를 생성합니다...")
        # 순수 파이썬 BMP 생성기
        for s in scenes:
            bmp_path = output_dir / s["filename"].replace(".png", ".bmp")
            width, height = 400, 300
            # 24-bit BMP header
            row_padded = (width * 3 + 3) & (~3)
            image_size = row_padded * height
            file_size = 54 + image_size

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

            r, g, b = s["bg_color"]
            ar, ag, ab = s["accent_color"]
            pixel_bytes = bytearray()
            for y in range(height):
                row = bytearray()
                for x in range(width):
                    # 테두리 또는 헤더 영역
                    if x < 10 or x >= width - 10 or y < 10 or y >= height - 10 or (220 <= y <= 270 and 20 <= x <= width - 20):
                        row.extend([ab, ag, ar])  # BGR
                    else:
                        row.extend([b, g, r])
                # 패딩
                while len(row) % 4 != 0:
                    row.append(0)
                pixel_bytes.extend(row)

            with open(bmp_path, "wb") as f:
                f.write(header)
                f.write(pixel_bytes)

            print(f"  ✓ 생성 완료: {bmp_path}")

    print(f"\n모든 샘플 이미지가 '{output_dir}/' 디렉토리에 준비되었습니다!")


if __name__ == "__main__":
    create_samples()
