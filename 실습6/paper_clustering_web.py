#!/usr/bin/env python3
"""
논문 유사도 군집화 인터랙티브 웹 애플리케이션 (paper_clustering_web.py)
==================================================================
외부 프레임워크(Flask, Streamlit 등) 설치 없이 파이썬 표준 라이브러리(http.server)만으로
동작하는 고기능 모던 반응형 웹 대시보드입니다.

주요 기능:
1. 웹 브라우저에서 K값(클러스터 개수) 실시간 슬라이더 조절 및 원클릭 재군집화
2. 2D / 3D PCA 차원 축소 산점도 실시간 렌더링 (마우스 드래그 3D 회전 지원)
3. 클러스터별 대표 도메인 및 키워드 요약 카드
4. 논문 카드 클릭 시 초록(Abstract) 및 상세 메타데이터 모달 팝업
5. 전체 논문 간 코사인 유사도(Cosine Similarity) 대화형 히트맵 매트릭스
6. 새로운 PDF 연구 논문 드래그 앤 드롭 업로드 및 실시간 색인

실행 방법:
    python paper_clustering_web.py
    # 브라우저에서 http://localhost:8505 접속
"""

import email
import http.server
import json
import os
import platform
import socketserver
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

from paper_cluster_engine import PaperClusteringEngine
from visualizer import CLUSTER_COLORS, PaperVisualizer

PORT = 8505
SCRIPT_DIR = Path(__file__).parent.resolve()
PAPERS_DIR = SCRIPT_DIR / "papers"

# 글로벌 엔진 인스턴스
ENGINE = PaperClusteringEngine(n_clusters=4, embedding_mode="auto")


def ensure_sample_papers():
    """샘플 논문이 없으면 자동 생성"""
    if not PAPERS_DIR.exists() or not list(PAPERS_DIR.glob("*.pdf")):
        from prepare_sample_papers import create_sample_papers
        create_sample_papers(str(PAPERS_DIR))
    ENGINE.load_papers(PAPERS_DIR)
    ENGINE.perform_clustering(k=4)


class PaperClusteringWebHandler(http.server.SimpleHTTPRequestHandler):
    """REST API 및 대시보드 UI를 제공하는 HTTP 핸들러"""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.render_dashboard_html().encode("utf-8"))
            return

        elif path == "/api/status":
            self.send_json_response({
                "status": "ok",
                "num_papers": len(ENGINE.papers),
                "k": ENGINE.n_clusters,
                "backend": ENGINE.embedding_engine.active_backend
            })
            return

        elif path == "/api/cluster":
            query = urllib.parse.parse_qs(parsed.query)
            k = int(query.get("k", [ENGINE.n_clusters])[0])
            ENGINE.perform_clustering(k=k)
            sim_matrix = ENGINE.compute_similarity_matrix()

            # 시각화 이미지 갱신
            try:
                PaperVisualizer.plot_clusters_2d(ENGINE.papers, ENGINE.cluster_summary, str(SCRIPT_DIR / "cluster_2d.png"))
                PaperVisualizer.plot_clusters_3d(ENGINE.papers, ENGINE.cluster_summary, str(SCRIPT_DIR / "cluster_3d.png"))
            except Exception:
                pass

            resp_data = {
                "k": k,
                "summary": [s for s in ENGINE.cluster_summary.values()],
                "papers": [p.to_dict() for p in ENGINE.papers],
                "similarity_matrix": [[round(float(v), 3) for v in row] for row in sim_matrix],
                "colors": CLUSTER_COLORS
            }
            self.send_json_response(resp_data)
            return

        elif path == "/cluster_2d.png":
            file_path = SCRIPT_DIR / "cluster_2d.png"
            if file_path.exists():
                self.serve_file(file_path, "image/png")
            else:
                self.send_error(404, "File not found")
            return

        elif path == "/cluster_3d.png":
            file_path = SCRIPT_DIR / "cluster_3d.png"
            if file_path.exists():
                self.serve_file(file_path, "image/png")
            else:
                self.send_error(404, "File not found")
            return

        elif path.startswith("/papers/"):
            # PDF 파일 서빙
            filename = Path(path).name
            target_pdf = PAPERS_DIR / filename
            if target_pdf.exists():
                self.serve_file(target_pdf, "application/pdf")
            else:
                self.send_error(404, "PDF not found")
            return

        # 기본 파일 서빙
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                self.send_error(400, "Bad request: multipart/form-data required")
                return

            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)

            header_bytes = f"Content-Type: {content_type}\r\n\r\n".encode("latin-1")
            msg = email.message_from_bytes(header_bytes + raw_body)

            saved_name = None
            if msg.is_multipart():
                for part in msg.get_payload():
                    fn = part.get_filename()
                    if fn or part.get_content_type() == "application/pdf":
                        payload = part.get_payload(decode=True)
                        if payload:
                            clean_fn = Path(fn).name if fn else f"Uploaded_Paper_{len(ENGINE.papers)+1}.pdf"
                            save_path = PAPERS_DIR / clean_fn
                            with open(save_path, "wb") as f:
                                f.write(payload)
                            saved_name = clean_fn
                            break

            if saved_name:
                # 재스캔 및 군집화
                ENGINE.load_papers(PAPERS_DIR)
                ENGINE.perform_clustering(k=ENGINE.n_clusters)
                self.send_json_response({"status": "success", "filename": saved_name, "total": len(ENGINE.papers)})
            else:
                self.send_error(400, "No valid file uploaded")
            return

        self.send_error(404, "Endpoint not found")

    def serve_file(self, file_path: Path, mime_type: str):
        with open(file_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json_response(self, data: Any):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def render_dashboard_html(self) -> str:
        """모던 웹 대시보드 HTML"""
        return """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI 연구 논문 의미론적 군집화 대시보드</title>
  <style>
    :root {
      --bg: #0B0F19;
      --surface: #151D2F;
      --surface-border: #23304B;
      --accent: #38BDF8;
      --accent-glow: rgba(56, 189, 248, 0.25);
      --text: #F1F5F9;
      --text-muted: #94A3B8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: var(--surface);
      border-bottom: 1px solid var(--surface-border);
      padding: 16px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand h1 {
      font-size: 20px;
      font-weight: 700;
      color: var(--accent);
    }
    .badge {
      background: #0284C7;
      color: white;
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 12px;
      font-weight: 600;
    }
    main {
      padding: 28px 32px;
      flex: 1;
      max-width: 1440px;
      margin: 0 auto;
      width: 100%;
    }
    /* Control Toolbar */
    .toolbar {
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 14px;
      padding: 18px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 16px;
    }
    .control-group {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .control-label {
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
    }
    .k-slider {
      width: 160px;
      accent-color: var(--accent);
      cursor: pointer;
    }
    .k-badge {
      background: var(--surface-border);
      padding: 4px 12px;
      border-radius: 8px;
      font-weight: 700;
      color: var(--accent);
      font-size: 16px;
    }
    .btn {
      background: var(--accent);
      color: #0B0F19;
      border: none;
      padding: 9px 20px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 14px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn:hover {
      box-shadow: 0 0 15px var(--accent-glow);
      transform: translateY(-1px);
    }
    /* Layout Grid */
    .dashboard-grid {
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 24px;
      margin-bottom: 30px;
    }
    @media (max-width: 1100px) {
      .dashboard-grid { grid-template-columns: 1fr; }
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 14px;
      padding: 22px;
    }
    .card-title {
      font-size: 16px;
      font-weight: 700;
      margin-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    /* Canvas */
    .canvas-box {
      width: 100%;
      height: 480px;
      background: #070B12;
      border-radius: 10px;
      position: relative;
      overflow: hidden;
      cursor: grab;
    }
    .canvas-box:active { cursor: grabbing; }
    canvas { width: 100%; height: 100%; display: block; }
    .tabs {
      display: flex;
      gap: 6px;
      background: #0B0F19;
      padding: 4px;
      border-radius: 8px;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .tab-btn.active {
      background: var(--accent);
      color: #0B0F19;
    }
    /* Cluster list */
    .cluster-list {
      display: flex;
      flex-direction: column;
      gap: 14px;
      max-height: 480px;
      overflow-y: auto;
      padding-right: 6px;
    }
    .cluster-item {
      background: #0B0F19;
      border: 1px solid var(--surface-border);
      border-radius: 10px;
      padding: 14px;
    }
    .cluster-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .c-tag {
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 700;
      color: white;
    }
    .paper-entry {
      background: #151D2F;
      border-radius: 6px;
      padding: 10px;
      margin-top: 8px;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.2s;
    }
    .paper-entry:hover {
      border-color: var(--accent);
    }
    .paper-entry h4 {
      font-size: 13px;
      font-weight: 600;
      color: var(--text);
    }
    .paper-entry p {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 3px;
    }
    /* Similarity Table */
    .table-container {
      overflow-x: auto;
      margin-top: 14px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    th, td {
      padding: 8px 12px;
      text-align: center;
      border: 1px solid var(--surface-border);
    }
    th {
      background: #0B0F19;
      color: var(--accent);
      font-weight: 600;
    }
    .heat-cell {
      font-weight: 600;
      border-radius: 4px;
    }
    /* Modal */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 20px;
    }
    .modal-content {
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 14px;
      max-width: 650px;
      width: 100%;
      padding: 26px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
      position: relative;
    }
    .close-btn {
      position: absolute;
      top: 18px;
      right: 20px;
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 22px;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>📚 PaperCluster AI</h1>
      <span class="badge">Research Paper Semantic Clustering</span>
    </div>
    <div style="font-size: 13px; color: var(--text-muted);">
      포트: <b>8505</b> | 로컬 전용 웹 대시보드
    </div>
  </header>

  <main>
    <!-- 컨트롤 툴바 -->
    <div class="toolbar">
      <div class="control-group">
        <span class="control-label">클러스터 개수 K 설정:</span>
        <input type="range" class="k-slider" id="kSlider" min="2" max="6" value="4" oninput="updateKVal(this.value)">
        <span class="k-badge" id="kBadge">K = 4</span>
      </div>
      <div class="control-group">
        <button class="btn" onclick="applyClustering()">⚡ 재군집화 실행</button>
      </div>
    </div>

    <!-- 대시보드 메인 그리드 -->
    <div class="dashboard-grid">
      <!-- 산점도 캔버스 -->
      <div class="card">
        <div class="card-title">
          <span>차원 축소 산점도 (Dimensionality Reduction)</span>
          <div class="tabs">
            <button class="tab-btn active" id="tab2d" onclick="setDim('2d')">2D 평면</button>
            <button class="tab-btn" id="tab3d" onclick="setDim('3d')">3D 공간</button>
          </div>
        </div>
        <div class="canvas-box" id="canvasBox">
          <canvas id="scatterCanvas"></canvas>
        </div>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 10px; display: flex; justify-content: space-between;">
          <span>💡 각 점은 논문 1편을 의미하며, 같은 색상은 동일 클러스터입니다.</span>
          <span id="hintText">2D 모드</span>
        </div>
      </div>

      <!-- 클러스터 목록 -->
      <div class="card">
        <div class="card-title">
          <span>군집화 결과 요약</span>
          <span id="totalPaperCount" style="font-size: 13px; color: var(--accent);">10편의 논문</span>
        </div>
        <div class="cluster-list" id="clusterList">
          <div style="text-align: center; color: var(--text-muted); padding: 40px;">데이터를 불러오는 중...</div>
        </div>
      </div>
    </div>

    <!-- 유사도 매트릭스 -->
    <div class="card">
      <div class="card-title">
        <span>논문 간 코사인 유사도 행렬 (Cosine Similarity Matrix)</span>
        <span style="font-size: 12px; color: var(--text-muted);">1.0에 가까울수록 내용이 의미론적으로 밀접함</span>
      </div>
      <div class="table-container" id="matrixContainer"></div>
    </div>
  </main>

  <!-- 상세 모달 -->
  <div class="modal-overlay" id="modalOverlay" onclick="closeModal(event)">
    <div class="modal-content" onclick="event.stopPropagation()">
      <button class="close-btn" onclick="closeModal()">&times;</button>
      <h3 id="modalTitle" style="color: var(--accent); margin-bottom: 8px; font-size: 17px;"></h3>
      <div id="modalMeta" style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;"></div>
      <h4 style="font-size: 14px; margin-bottom: 6px;">초록 (Abstract)</h4>
      <div id="modalAbstract" style="font-size: 13px; line-height: 1.6; color: #CBD5E1; background: #0B0F19; padding: 14px; border-radius: 8px; max-height: 250px; overflow-y: auto;"></div>
      <h4 style="font-size: 14px; margin: 14px 0 6px 0;">핵심 키워드 (Keywords)</h4>
      <div id="modalKeywords" style="font-size: 12px; color: var(--accent);"></div>
    </div>
  </div>

  <script>
    let currentK = 4;
    let currentDim = '2d';
    let papersData = [];
    let clustersData = [];
    let simMatrix = [];
    let colorPalette = [];

    const canvas = document.getElementById('scatterCanvas');
    const ctx = canvas.getContext('2d');
    const box = document.getElementById('canvasBox');

    let rotX = 0.35, rotY = 0.45;
    let isDragging = false;
    let lastX = 0, lastY = 0;

    function updateKVal(val) {
      currentK = parseInt(val);
      document.getElementById('kBadge').textContent = 'K = ' + val;
    }

    function setDim(dim) {
      currentDim = dim;
      document.getElementById('tab2d').classList.toggle('active', dim === '2d');
      document.getElementById('tab3d').classList.toggle('active', dim === '3d');
      document.getElementById('hintText').textContent = dim === '3d' ? '3D 모드 (마우스 드래그 회전)' : '2D 모드';
      renderChart();
    }

    async function applyClustering() {
      const res = await fetch(`/api/cluster?k=${currentK}`);
      const data = await res.json();
      papersData = data.papers;
      clustersData = data.summary;
      simMatrix = data.similarity_matrix;
      colorPalette = data.colors;

      document.getElementById('totalPaperCount').textContent = `총 ${papersData.length}편 분석됨`;
      renderClusterList();
      renderMatrix();
      renderChart();
    }

    function renderClusterList() {
      const container = document.getElementById('clusterList');
      container.innerHTML = '';

      clustersData.forEach(c => {
        const color = colorPalette[c.cluster_id % colorPalette.length];
        const card = document.createElement('div');
        card.className = 'cluster-item';

        const kwStr = c.top_keywords.slice(0, 4).join(', ');
        card.innerHTML = `
          <div class="cluster-header">
            <span class="c-tag" style="background: ${color}">Cluster #${c.cluster_id}: ${c.dominant_category}</span>
            <span style="font-size: 12px; color: var(--text-muted); font-weight: 600;">${c.count}편</span>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px;">
            🔑 <b>키워드:</b> ${kwStr || '없음'}
          </div>
          <div>
            ${c.papers.map(p => `
              <div class="paper-entry" onclick="openModal(${p.doc_id})">
                <h4>📄 ${p.title}</h4>
                <p>✍️ ${p.authors || '저자 미상'} | 📁 ${p.filename}</p>
              </div>
            `).join('')}
          </div>
        `;
        container.appendChild(card);
      });
    }

    function renderMatrix() {
      const cont = document.getElementById('matrixContainer');
      if (!simMatrix.length) return;

      let html = '<table><thead><tr><th>논문 번호</th>';
      for (let i = 0; i < papersData.length; i++) {
        html += `<th>#${i+1}</th>`;
      }
      html += '</tr></thead><tbody>';

      for (let i = 0; i < papersData.length; i++) {
        const p1 = papersData[i];
        html += `<tr><td style="text-align: left; font-weight: 600;">#${i+1} ${p1.filename.split('_')[0]}</td>`;
        for (let j = 0; j < papersData.length; j++) {
          const val = simMatrix[i][j];
          let bg = 'transparent';
          let textColor = '#94A3B8';
          if (i === j) {
            bg = '#0284C7'; textColor = '#FFF';
          } else if (val > 0.15) {
            bg = 'rgba(56, 189, 248, 0.4)'; textColor = '#FFF';
          } else if (val > 0.08) {
            bg = 'rgba(56, 189, 248, 0.15)'; textColor = '#CBD5E1';
          }
          html += `<td style="background: ${bg}; color: ${textColor};" class="heat-cell">${val.toFixed(2)}</td>`;
        }
        html += '</tr>';
      }
      html += '</tbody></table>';
      cont.innerHTML = html;
    }

    function renderChart() {
      canvas.width = box.clientWidth * window.devicePixelRatio;
      canvas.height = box.clientHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

      const w = box.clientWidth;
      const h = box.clientHeight;
      ctx.clearRect(0, 0, w, h);

      if (currentDim === '2d') {
        const xs = papersData.map(p => p.pca_2d ? p.pca_2d[0] : 0);
        const ys = papersData.map(p => p.pca_2d ? p.pca_2d[1] : 0);
        const minX = Math.min(...xs), maxX = Math.max(...xs);
        const minY = Math.min(...ys), maxY = Math.max(...ys);
        const padX = (maxX - minX) * 0.2 || 0.1;
        const padY = (maxY - minY) * 0.2 || 0.1;

        papersData.forEach(p => {
          if (!p.pca_2d) return;
          const px = ((p.pca_2d[0] - (minX - padX)) / ((maxX + padX) - (minX - padX))) * (w - 120) + 60;
          const py = (1 - (p.pca_2d[1] - (minY - padY)) / ((maxY + padY) - (minY - padY))) * (h - 100) + 50;
          const color = colorPalette[p.cluster_id % colorPalette.length];

          ctx.beginPath();
          ctx.arc(px, py, 9, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.strokeStyle = '#FFFFFF';
          ctx.lineWidth = 1.8;
          ctx.stroke();

          ctx.font = '11px sans-serif';
          ctx.fillStyle = '#CBD5E1';
          const label = p.title.length > 18 ? p.title.substring(0, 18) + '...' : p.title;
          ctx.fillText(label, px + 12, py + 4);
        });
      } else {
        const cx = w / 2, cy = h / 2;
        const scale = Math.min(w, h) * 0.42;
        const cosX = Math.cos(rotX), sinX = Math.sin(rotX);
        const cosY = Math.cos(rotY), sinY = Math.sin(rotY);

        papersData.forEach(p => {
          if (!p.pca_3d) return;
          const [x0, y0, z0] = p.pca_3d;
          const x1 = x0 * cosY + z0 * sinY;
          const y1 = y0;
          const z1 = -x0 * sinY + z0 * cosY;

          const x2 = x1;
          const y2 = y1 * cosX - z1 * sinX;
          const z2 = y1 * sinX + z1 * cosX;

          const fov = 3.5;
          const depth = fov / (fov + z2);
          const px = cx + x2 * scale * depth;
          const py = cy - y2 * scale * depth;
          const color = colorPalette[p.cluster_id % colorPalette.length];

          ctx.beginPath();
          ctx.arc(px, py, Math.max(5, 9 * depth), 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.strokeStyle = '#FFFFFF';
          ctx.lineWidth = 1.5;
          ctx.stroke();

          ctx.font = '10px sans-serif';
          ctx.fillStyle = '#94A3B8';
          ctx.fillText(p.filename.split('_')[0], px + 10, py + 3);
        });
      }
    }

    box.addEventListener('mousedown', e => {
      isDragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
    });
    window.addEventListener('mouseup', () => isDragging = false);
    box.addEventListener('mousemove', e => {
      if (isDragging && currentDim === '3d') {
        rotY += (e.clientX - lastX) * 0.01;
        rotX += (e.clientY - lastY) * 0.01;
        lastX = e.clientX;
        lastY = e.clientY;
        renderChart();
      }
    });

    function openModal(docId) {
      const p = papersData.find(x => x.doc_id === docId);
      if (!p) return;
      document.getElementById('modalTitle').textContent = p.title;
      document.getElementById('modalMeta').innerHTML = `
        저자: <b>${p.authors || '저자 미상'}</b> | 분류: <b>Cluster #${p.cluster_id} (${p.category_hint})</b><br>
        파일명: ${p.filename} | 저널: ${p.journal || '학술 저널'}
      `;
      document.getElementById('modalAbstract').textContent = p.abstract;
      document.getElementById('modalKeywords').textContent = p.keywords || '키워드 없음';
      document.getElementById('modalOverlay').style.display = 'flex';
    }

    function closeModal(e) {
      document.getElementById('modalOverlay').style.display = 'none';
    }

    window.addEventListener('resize', renderChart);
    window.addEventListener('DOMContentLoaded', applyClustering);
  </script>
</body>
</html>
"""


def run_web_server(port: int = PORT, auto_open: bool = True):
    """경량 웹 대시보드 서버 구동"""
    ensure_sample_papers()

    handler = PaperClusteringWebHandler
    # 포트 재사용 소켓 설정
    socketserver.TCPServer.allow_reuse_address = True

    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            url = f"http://localhost:{port}"
            print("\n" + "=" * 70)
            print(" 🌐 논문 군집화 인터랙티브 웹 대시보드가 준비되었습니다!")
            print("=" * 70)
            print(f" • 대시보드 주소: {url}")
            print(f" • 대상 논문 폴더: {PAPERS_DIR} ({len(ENGINE.papers)}편 인덱싱됨)")
            print(f" • 조작 안내     : 슬라이더로 K값 변경 및 2D/3D 시각화 실시간 확인")
            print(" • 종료 방법     : Ctrl + C 를 누르면 서버가 안전하게 종료됩니다.")
            print("=" * 70 + "\n")

            if auto_open:
                try:
                    current_os = platform.system()
                    if current_os == "Darwin":
                        subprocess.run(["open", url])
                    elif current_os == "Windows":
                        os.startfile(url)
                    else:
                        subprocess.run(["xdg-open", url])
                except Exception:
                    pass

            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 웹 서버를 종료합니다.")
    except Exception as e:
        print(f"❌ 웹 서버 실행 실패: {e}")


if __name__ == "__main__":
    run_web_server(PORT, auto_open=False)
