"""
논문 군집화 시각화 모듈 (visualizer.py)
=====================================
주요 기능:
1. 2D PCA 산점도 생성 및 PNG 저장 (Matplotlib 기반)
2. 3D PCA 3차원 공간 산점도 생성 및 PNG 저장 (Matplotlib 기반)
3. 브라우저에서 열람 가능한 모던 인터랙티브 HTML 2D/3D 시각화 리포트 생성
   (마우스 호버 시 논문 제목, 요약 툴팁, 클러스터 필터링, 유사도 매트릭스 뷰어)
"""

import json
import math
import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# Matplotlib 지원 확인
try:
    import matplotlib
    # 비대화형 백엔드 설정 (서버/헤드리스 환경 호환)
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# 도메인/클러스터별 프리미엄 색상 팔레트
CLUSTER_COLORS = [
    "#4361EE",  # 로열 블루 (AI/Tech)
    "#E63946",  # 코랄 레드 (Biomedical)
    "#2A9D8F",  # 틸/에메랄드 (Climate/Renewable)
    "#F4A261",  # 오렌지 골드 (Fintech)
    "#7209B7",  # 바이올렛 퍼플
    "#3A0CA3",  # 딥 인디고
    "#4CC9F0",  # 스카이 블루
    "#06D6A0"   # 민트 그린
]


class PaperVisualizer:
    """논문 임베딩 및 클러스터링 결과 시각화 도구"""

    @staticmethod
    def plot_clusters_2d(
        papers: List[Any],
        cluster_summary: Dict[int, Any],
        output_path: str = "cluster_2d.png",
        show_labels: bool = True
    ) -> Optional[str]:
        """Matplotlib을 사용한 고해상도 2D PCA 산점도 저장"""
        if not HAS_MATPLOTLIB:
            print("⚠️ Matplotlib이 설치되어 있지 않아 2D PNG 생성을 건너뜁니다.")
            return None

        # 한글 폰트 설정 시도
        system_os = platform.system()
        if system_os == "Darwin":
            plt.rcParams["font.family"] = "AppleGothic"
        elif system_os == "Windows":
            plt.rcParams["font.family"] = "Malgun Gothic"
        plt.rcParams["axes.unicode_minus"] = False

        fig, ax = plt.subplots(figsize=(12, 8), dpi=200)
        fig.patch.set_facecolor("#FAFAFA")
        ax.set_facecolor("#FFFFFF")

        # 그리드 및 스타일 설정
        ax.grid(True, linestyle="--", alpha=0.35, color="#CCCCCC")
        ax.set_axisbelow(True)

        # 클러스터별 플로팅
        for c_id, summary in cluster_summary.items():
            color = CLUSTER_COLORS[c_id % len(CLUSTER_COLORS)]
            c_papers = [p for p in papers if p.cluster_id == c_id]

            xs = [p.pca_2d[0] for p in c_papers if p.pca_2d is not None]
            ys = [p.pca_2d[1] for p in c_papers if p.pca_2d is not None]

            if not xs:
                continue

            label_name = f"Cluster {c_id}: {summary.get('dominant_category', 'General')} ({len(c_papers)}편)"
            ax.scatter(
                xs, ys,
                c=color,
                s=160,
                alpha=0.88,
                edgecolors="#FFFFFF",
                linewidth=1.8,
                label=label_name,
                zorder=4
            )

            # 중심점 계산 및 X 마커 표시
            center_x = float(sum(xs) / len(xs))
            center_y = float(sum(ys) / len(ys))
            ax.scatter(
                [center_x], [center_y],
                c=color,
                s=280,
                marker="X",
                edgecolors="#333333",
                linewidth=2.0,
                alpha=0.95,
                zorder=5
            )

            # 논문 제목 레이블링
            if show_labels:
                for p in c_papers:
                    if p.pca_2d is not None:
                        # 긴 제목 줄임표 처리
                        title_label = p.title[:28] + "..." if len(p.title) > 28 else p.title
                        ax.annotate(
                            title_label,
                            (p.pca_2d[0], p.pca_2d[1]),
                            xytext=(8, 6),
                            textcoords="offset points",
                            fontsize=8.5,
                            alpha=0.85,
                            fontweight="medium",
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFFFFF", alpha=0.7, edgecolor="#DDDDDD", linewidth=0.5)
                        )

        ax.set_title("Research Paper Semantic Clustering (2D PCA Projection)", fontsize=15, fontweight="bold", pad=16, color="#222222")
        ax.set_xlabel("Principal Component 1 (PC1)", fontsize=11, fontweight="bold", labelpad=10, color="#444444")
        ax.set_ylabel("Principal Component 2 (PC2)", fontsize=11, fontweight="bold", labelpad=10, color="#444444")

        # 범례 스타일링
        legend = ax.legend(
            loc="upper right",
            frameon=True,
            facecolor="#FFFFFF",
            edgecolor="#E0E0E0",
            fontsize=9.5,
            framealpha=0.92
        )
        legend.get_title().set_fontweight("bold")

        plt.tight_layout()
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out_file), bbox_inches="tight")
        plt.close(fig)
        return str(out_file)

    @staticmethod
    def plot_clusters_3d(
        papers: List[Any],
        cluster_summary: Dict[int, Any],
        output_path: str = "cluster_3d.png"
    ) -> Optional[str]:
        """Matplotlib 3D projection을 사용한 3차원 PCA 산점도 저장"""
        if not HAS_MATPLOTLIB:
            print("⚠️ Matplotlib이 설치되어 있지 않아 3D PNG 생성을 건너뜁니다.")
            return None

        fig = plt.figure(figsize=(13, 9), dpi=200)
        fig.patch.set_facecolor("#FAFAFA")
        ax = fig.add_subplot(111, projection="3d")
        ax.set_facecolor("#FFFFFF")

        for c_id, summary in cluster_summary.items():
            color = CLUSTER_COLORS[c_id % len(CLUSTER_COLORS)]
            c_papers = [p for p in papers if p.cluster_id == c_id]

            xs = [p.pca_3d[0] for p in c_papers if p.pca_3d is not None]
            ys = [p.pca_3d[1] for p in c_papers if p.pca_3d is not None]
            zs = [p.pca_3d[2] for p in c_papers if p.pca_3d is not None]

            if not xs:
                continue

            label_name = f"Cluster {c_id}: {summary.get('dominant_category', 'General')}"
            ax.scatter(
                xs, ys, zs,
                c=color,
                s=140,
                alpha=0.85,
                edgecolors="#FFFFFF",
                linewidth=1.2,
                label=label_name
            )

            # 제목 축약 표기
            for p in c_papers:
                if p.pca_3d is not None:
                    short_name = p.filename.split("_")[0] + "_" + p.filename.split("_")[1]
                    ax.text(p.pca_3d[0], p.pca_3d[1], p.pca_3d[2], f" {short_name}", fontsize=7.5, alpha=0.8)

        ax.set_title("Research Paper Semantic Clustering (3D PCA Space)", fontsize=14, fontweight="bold", pad=14)
        ax.set_xlabel("PC 1", fontsize=10, labelpad=8)
        ax.set_ylabel("PC 2", fontsize=10, labelpad=8)
        ax.set_zlabel("PC 3", fontsize=10, labelpad=8)
        ax.legend(loc="upper left", fontsize=9, framealpha=0.9)

        # 보기 좋은 초기 시야각 설정
        ax.view_init(elev=24, azim=45)

        plt.tight_layout()
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out_file), bbox_inches="tight")
        plt.close(fig)
        return str(out_file)

    @staticmethod
    def generate_interactive_html(
        papers: List[Any],
        cluster_summary: Dict[int, Any],
        similarity_matrix: Optional[Any] = None,
        output_path: str = "cluster_interactive.html"
    ) -> str:
        """
        웹 브라우저에서 마우스 인터랙션(회전, 호버, 줌, 필터링, 유사도 검사)이 가능한
        완전 독립형(Single File) 모던 대시보드 HTML 파일 생성.
        """
        # 데이터 JSON 직렬화
        papers_data = []
        for p in papers:
            papers_data.append({
                "id": p.doc_id,
                "filename": p.filename,
                "title": p.title,
                "authors": p.authors,
                "journal": p.journal,
                "category": p.category_hint,
                "abstract": p.abstract,
                "keywords": p.keywords,
                "cluster_id": p.cluster_id,
                "color": CLUSTER_COLORS[p.cluster_id % len(CLUSTER_COLORS)],
                "x2d": round(float(p.pca_2d[0]), 4) if p.pca_2d else 0.0,
                "y2d": round(float(p.pca_2d[1]), 4) if p.pca_2d else 0.0,
                "x3d": round(float(p.pca_3d[0]), 4) if p.pca_3d else 0.0,
                "y3d": round(float(p.pca_3d[1]), 4) if p.pca_3d else 0.0,
                "z3d": round(float(p.pca_3d[2]), 4) if p.pca_3d else 0.0,
            })

        summary_data = []
        for c_id, s in cluster_summary.items():
            summary_data.append({
                "id": c_id,
                "color": CLUSTER_COLORS[c_id % len(CLUSTER_COLORS)],
                "category": s.get("dominant_category", f"Cluster {c_id}"),
                "count": s.get("count", 0),
                "keywords": s.get("top_keywords", [])[:5]
            })

        sim_data = []
        if similarity_matrix is not None:
            sim_data = [[round(float(v), 3) for v in row] for row in similarity_matrix]

        html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>논문 유사도 기반 군집화 인터랙티브 리포트</title>
  <style>
    :root {{
      --bg-color: #0F172A;
      --card-bg: #1E293B;
      --card-border: #334155;
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --accent: #38BDF8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg-color);
      color: var(--text-main);
      padding: 24px;
      line-height: 1.5;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--card-border);
    }}
    .header h1 {{
      font-size: 24px;
      font-weight: 700;
      color: #38BDF8;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .header p {{ color: var(--text-muted); font-size: 14px; margin-top: 4px; }}
    .stats-bar {{
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
      flex-wrap: wrap;
    }}
    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px 20px;
      flex: 1;
      min-width: 200px;
    }}
    .stat-title {{ font-size: 13px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }}
    .stat-value {{ font-size: 22px; font-weight: 700; color: #F1F5F9; margin-top: 6px; }}
    .grid-container {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 24px;
    }}
    @media (max-width: 1024px) {{
      .grid-container {{ grid-template-columns: 1fr; }}
    }}
    .chart-panel {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 20px;
      position: relative;
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }}
    .tab-group {{
      display: flex;
      background: #0F172A;
      border-radius: 8px;
      padding: 4px;
      gap: 4px;
    }}
    .tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .tab-btn.active {{
      background: #38BDF8;
      color: #0F172A;
    }}
    #canvas-container {{
      position: relative;
      width: 100%;
      height: 520px;
      background: #090D16;
      border-radius: 10px;
      overflow: hidden;
      cursor: grab;
    }}
    #canvas-container:active {{ cursor: grabbing; }}
    canvas {{ width: 100%; height: 100%; display: block; }}
    .side-panel {{
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    .cluster-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
    }}
    .cluster-badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 10px;
      color: #FFF;
    }}
    .kw-tag {{
      display: inline-block;
      background: #334155;
      color: #CBD5E1;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      margin: 2px 4px 2px 0;
    }}
    .paper-list-item {{
      background: #0F172A;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px;
      margin-top: 8px;
      cursor: pointer;
      transition: border-color 0.2s;
    }}
    .paper-list-item:hover {{
      border-color: #38BDF8;
    }}
    .paper-item-title {{
      font-size: 13px;
      font-weight: 600;
      color: #F8FAFC;
    }}
    .paper-item-meta {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
    }}
    .tooltip {{
      position: absolute;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid #38BDF8;
      border-radius: 8px;
      padding: 12px 16px;
      color: #F8FAFC;
      font-size: 12px;
      pointer-events: none;
      display: none;
      max-width: 320px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      z-index: 100;
    }}
    .tooltip-title {{ font-weight: 700; font-size: 13px; margin-bottom: 4px; color: #38BDF8; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>📚 논문 유사도 기반 의미론적 군집화 (Semantic Paper Clustering)</h1>
      <p>PDF 텍스트 추출 & 벡터 임베딩 & K-Means 군집화 & PCA 2D/3D 차원 축소 결과 대시보드</p>
    </div>
  </div>

  <div class="stats-bar" id="stats-bar">
    <div class="stat-card">
      <div class="stat-title">총 분석 논문</div>
      <div class="stat-value">{len(papers)} 편</div>
    </div>
    <div class="stat-card">
      <div class="stat-title">군집(Clusters) 개수 K</div>
      <div class="stat-value">{len(cluster_summary)} 개</div>
    </div>
    <div class="stat-card">
      <div class="stat-title">임베딩 차원 축소</div>
      <div class="stat-value">PCA (2D / 3D)</div>
    </div>
  </div>

  <div class="grid-container">
    <!-- 좌측: 인터랙티브 차트 -->
    <div class="chart-panel">
      <div class="panel-header">
        <h2 style="font-size: 16px; font-weight: 600;">차원 축소 산점도 (Scatter Plot)</h2>
        <div class="tab-group">
          <button class="tab-btn active" id="btn-2d" onclick="switchDim('2d')">2D 평면 투영</button>
          <button class="tab-btn" id="btn-3d" onclick="switchDim('3d')">3D 공간 회전</button>
        </div>
      </div>
      <div id="canvas-container">
        <canvas id="clusterCanvas"></canvas>
        <div id="tooltip" class="tooltip"></div>
      </div>
      <div style="font-size: 12px; color: var(--text-muted); margin-top: 10px; display: flex; justify-content: space-between;">
        <span>💡 포인트에 마우스를 올리면 논문 상세 정보를 확인하실 수 있습니다.</span>
        <span id="control-hint">3D 모드: 마우스 드래그로 회전 가능</span>
      </div>
    </div>

    <!-- 우측: 클러스터 요약 및 논문 목록 -->
    <div class="side-panel" id="side-panel"></div>
  </div>

  <script>
    const papers = {json.dumps(papers_data, ensure_ascii=False)};
    const clusters = {json.dumps(summary_data, ensure_ascii=False)};
    const simMatrix = {json.dumps(sim_data)};

    let currentDim = '2d';
    const canvas = document.getElementById('clusterCanvas');
    const ctx = canvas.getContext('2d');
    const tooltip = document.getElementById('tooltip');
    const container = document.getElementById('canvas-container');

    // 3D 뷰 회전 각도
    let rotX = 0.35;
    let rotY = 0.45;
    let isDragging = false;
    let lastMouseX = 0;
    let lastMouseY = 0;

    function resizeCanvas() {{
      canvas.width = container.clientWidth * window.devicePixelRatio;
      canvas.height = container.clientHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      draw();
    }}
    window.addEventListener('resize', resizeCanvas);

    function switchDim(dim) {{
      currentDim = dim;
      document.getElementById('btn-2d').classList.toggle('active', dim === '2d');
      document.getElementById('btn-3d').classList.toggle('active', dim === '3d');
      document.getElementById('control-hint').textContent = dim === '3d' ? '3D 모드: 마우스 드래그로 360도 회전' : '2D 모드: 평면 PCA 투영';
      draw();
    }}

    // 렌더링 루프
    function draw() {{
      const width = container.clientWidth;
      const height = container.clientHeight;
      ctx.clearRect(0, 0, width, height);

      if (currentDim === '2d') {{
        draw2D(width, height);
      }} else {{
        draw3D(width, height);
      }}
    }}

    function draw2D(w, h) {{
      // 2D 스케일 계산
      const xs = papers.map(p => p.x2d);
      const ys = papers.map(p => p.y2d);
      const minX = Math.min(...xs), maxX = Math.max(...xs);
      const minY = Math.min(...ys), maxY = Math.max(...ys);
      const padX = (maxX - minX) * 0.18 || 0.1;
      const padY = (maxY - minY) * 0.18 || 0.1;

      function toScreen(x, y) {{
        const sx = ((x - (minX - padX)) / ((maxX + padX) - (minX - padX))) * (w - 120) + 60;
        const sy = (1 - (y - (minY - padY)) / ((maxY + padY) - (minY - padY))) * (h - 100) + 50;
        return [sx, sy];
      }}

      // 중심선 가이드
      ctx.strokeStyle = '#1E293B';
      ctx.lineWidth = 1;
      const [midX, midY] = toScreen(0, 0);
      ctx.beginPath();
      ctx.moveTo(0, midY); ctx.lineTo(w, midY);
      ctx.moveTo(midX, 0); ctx.lineTo(midX, h);
      ctx.stroke();

      // 포인트 그리기
      papers.forEach(p => {{
        const [px, py] = toScreen(p.x2d, p.y2d);
        p._screenX = px;
        p._screenY = py;

        // 원형 포인트
        ctx.beginPath();
        ctx.arc(px, py, 9, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#FFFFFF';
        ctx.stroke();

        // 텍스트 라벨
        ctx.font = '11px sans-serif';
        ctx.fillStyle = '#CBD5E1';
        ctx.fillText(p.title.length > 20 ? p.title.substring(0, 20) + '...' : p.title, px + 12, py + 4);
      }});
    }}

    function draw3D(w, h) {{
      const cx = w / 2;
      const cy = h / 2;
      const scale = Math.min(w, h) * 0.42;

      // 3D 회전 행렬 적용
      const cosX = Math.cos(rotX), sinX = Math.sin(rotX);
      const cosY = Math.cos(rotY), sinY = Math.sin(rotY);

      // 좌표 변환 및 정렬
      const projected = papers.map(p => {{
        // Y축 회전
        let x1 = p.x3d * cosY + p.z3d * sinY;
        let y1 = p.y3d;
        let z1 = -p.x3d * sinY + p.z3d * cosY;

        // X축 회전
        let x2 = x1;
        let y2 = y1 * cosX - z1 * sinX;
        let z2 = y1 * sinX + z1 * cosX;

        const fov = 3.5;
        const depth = fov / (fov + z2);
        const px = cx + x2 * scale * depth;
        const py = cy - y2 * scale * depth;

        return {{ paper: p, px, py, z2, depth }};
      }});

      // 뒤에서 앞으로 정렬
      projected.sort((a, b) => b.z2 - a.z2);

      // 박스 가이드라인
      ctx.strokeStyle = '#334155';
      ctx.lineWidth = 1;
      ctx.strokeRect(cx - scale * 0.8, cy - scale * 0.8, scale * 1.6, scale * 1.6);

      projected.forEach(item => {{
        const p = item.paper;
        p._screenX = item.px;
        p._screenY = item.py;

        const radius = Math.max(5, 9 * item.depth);
        ctx.beginPath();
        ctx.arc(item.px, item.py, radius, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = '#FFFFFF';
        ctx.stroke();

        ctx.font = '10px sans-serif';
        ctx.fillStyle = '#94A3B8';
        ctx.fillText(p.filename.split('_')[0], item.px + 10, item.py + 3);
      }});
    }}

    // 마우스 인터랙션 (호버 툴팁)
    container.addEventListener('mousemove', e => {{
      const rect = container.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      if (isDragging && currentDim === '3d') {{
        const dx = mouseX - lastMouseX;
        const dy = mouseY - lastMouseY;
        rotY += dx * 0.01;
        rotX += dy * 0.01;
        lastMouseX = mouseX;
        lastMouseY = mouseY;
        draw();
        return;
      }}

      // 호버 대상 감지
      let hovered = null;
      for (let p of papers) {{
        if (p._screenX !== undefined && p._screenY !== undefined) {{
          const dist = Math.hypot(p._screenX - mouseX, p._screenY - mouseY);
          if (dist < 14) {{
            hovered = p;
            break;
          }}
        }}
      }}

      if (hovered) {{
        tooltip.style.display = 'block';
        tooltip.style.left = (mouseX + 15) + 'px';
        tooltip.style.top = (mouseY + 15) + 'px';
        tooltip.innerHTML = `
          <div class="tooltip-title">${{hovered.title}}</div>
          <div style="color: var(--text-muted); margin-bottom: 6px;">
            클러스터: <b>Cluster ${{hovered.cluster_id}}</b> (${{hovered.category}})<br>
            파일: ${{hovered.filename}}
          </div>
          <div style="font-size: 11px; line-height: 1.4; color: #E2E8F0;">
            ${{hovered.abstract.substring(0, 160)}}...
          </div>
        `;
      }} else {{
        tooltip.style.display = 'none';
      }}
    }});

    container.addEventListener('mousedown', e => {{
      isDragging = true;
      const rect = container.getBoundingClientRect();
      lastMouseX = e.clientX - rect.left;
      lastMouseY = e.clientY - rect.top;
    }});

    window.addEventListener('mouseup', () => {{
      isDragging = false;
    }});

    // 사이드 패널 채우기
    const sidePanel = document.getElementById('side-panel');
    clusters.forEach(c => {{
      const card = document.createElement('div');
      card.className = 'cluster-card';
      const cPapers = papers.filter(p => p.cluster_id === c.id);

      card.innerHTML = `
        <div class="cluster-badge" style="background: ${{c.color}}">
          Cluster ${{c.id}}: ${{c.category}} (${{c.count}}편)
        </div>
        <div style="margin-bottom: 10px;">
          ${{c.keywords.map(kw => `<span class="kw-tag">#${{kw}}</span>`).join('')}}
        </div>
        <div>
          ${{cPapers.map(p => `
            <div class="paper-list-item" onclick="focusPaper(${{p.id}})">
              <div class="paper-item-title">📄 ${{p.title}}</div>
              <div class="paper-item-meta">저자: ${{p.authors || '정보 없음'}}</div>
            </div>
          `).join('')}}
        </div>
      `;
      sidePanel.appendChild(card);
    }});

    function focusPaper(id) {{
      const p = papers.find(x => x.id === id);
      if (!p) return;
      alert(`[논문 정보]\\n제목: ${{p.title}}\\n분류: Cluster ${{p.cluster_id}} (${{p.category}})\\n파일명: ${{p.filename}}\\n키워드: ${{p.keywords}}\\n\\n초록(Abstract):\\n${{p.abstract}}`);
    }}

    setTimeout(resizeCanvas, 50);
  </script>
</body>
</html>
"""
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_template)
        return str(out_file)
