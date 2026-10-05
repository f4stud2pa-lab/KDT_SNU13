# 📚 논문 유사도 기반 의미론적 군집화 (Research Paper Semantic Clustering)

PDF 형식의 연구 논문들을 읽고, 각 논문의 본문과 요약(Abstract)을 고차원 벡터 임베딩으로 변환한 뒤 코사인 유사도(Cosine Similarity)를 계산하고 **K-Means 군집화**를 수행하는 Python 프로그램입니다. 또한 군집화 결과를 **PCA(주성분 분석) 2D 및 3D 산점도**로 시각화합니다.

---

## 🌟 주요 특징 및 세부 요구사항 구현 내역

| 요구사항 | 구현 방식 및 상세 설명 |
| :--- | :--- |
| **1. 논문 PDF 데이터 준비** | • 4개 학술 도메인(AI/딥러닝, 블록체인/핀테크, 기후/신재생, 바이오/유전체) 총 10편의 정규 연구 논문 PDF 제공 (`papers/`)<br>• 실제 Title, Authors, Abstract, Keywords, Sections 구조 포함 |
| **2. PDF 텍스트 추출** | • `pypdf` 지원 및 외부 의존성 없는 **내장 순수 파이썬 PDF 1.4 스트림 디코더** 완비<br>• 문서의 제목(Title), 초록(Abstract), 키워드, 본문 텍스트 자동 파싱 |
| **3. 텍스트 임베딩 생성** | • **OpenAI API** (`text-embedding-3-small`, 1536차원) 지원<br>• 오프라인 환경을 위한 **고성능 Sublinear TF-IDF + N-gram(1~2) 벡터라이저** 내장 (L2 단위 정규화) |
| **4. 유사도 계산 및 군집화** | • 코사인 유사도(Cosine Similarity) 대칭 행렬 계산<br>• **K-Means 군집화** (K-Means++ 스마트 초기화, 다중 재시작 n_init=10)<br>• **사용자가 클러스터 개수 K를 직접 지정** 가능 (CLI `-k`, 대화형 입력, 웹 UI 슬라이더)<br>• Elbow Method 기반 **최적 K 추천 기능** 제공 |
| **5. 결과 출력** | • 각 클러스터 번호 및 대표 키워드(Top Keywords) 출력<br>• 각 클러스터에 속한 논문 제목, 파일명, 저자, 초록 요약본 및 2D 투영 좌표 출력<br>• 각 논문별 가장 유사한 Top-1 매칭 및 동일 클러스터 판별 결과 출력 |
| **6. 2D / 3D 시각화** | • **2D PCA 산점도** (`cluster_2d.png`): 클러스터별 색상, 중심점(X), 논문 제목 주석 말풍선<br>• **3D PCA 산점도** (`cluster_3d.png`): 3차원 공간 투영 시각화<br>• **인터랙티브 웹 대시보드** (`cluster_interactive.html`): 마우스 호버 시 논문 정보 툴팁, 360도 3D 회전, 클러스터 필터링 |
| **7. 웹 인터페이스** | • 브라우저에서 K값 슬라이더 조절, 원클릭 재군집화, 논문 상세 모달, 유사도 히트맵 제공 (`paper_clustering_web.py`) |

---

## 📁 디렉토리 구조

```
실습6/
├── papers/                                  # 테스트용 연구 논문 PDF 10편
│   ├── AI_01_Transformer_Language_Models.pdf
│   ├── AI_02_Computer_Vision_Residual_Networks.pdf
│   ├── AI_03_Reinforcement_Learning_Human_Feedback.pdf
│   ├── FinTech_01_Automated_Market_Makers.pdf
│   ├── FinTech_02_Proof_of_Stake_Consensus.pdf
│   ├── FinTech_03_Algorithmic_High_Frequency_Trading.pdf
│   ├── Climate_01_Perovskite_Solar_Cells.pdf
│   ├── Climate_02_Ocean_Circulation_Carbon_Capture.pdf
│   ├── Bio_01_CRISPR_Cas9_Gene_Editing.pdf
│   └── Bio_02_Single_Cell_RNA_Cancer_Immunology.pdf
├── prepare_sample_papers.py                 # 연구 논문 PDF 10편 자동 생성 스크립트
├── paper_cluster_engine.py                  # PDF 파서, TF-IDF/임베딩, K-Means, PCA 핵심 엔진
├── visualizer.py                            # Matplotlib 2D/3D 플롯 및 인터랙티브 HTML 시각화
├── paper_clustering.py                      # 메인 CLI 프로그램 (K값 지정 및 결과 출력)
├── paper_clustering_web.py                  # 인터랙티브 웹 대시보드 애플리케이션
├── test_clustering.py                       # 전체 파이프라인 자동 검증 단위 테스트 (5개 테스트)
├── requirements.txt                         # 의존성 패키지 목록
├── cluster_2d.png                           # 생성된 2D PCA 산점도
├── cluster_3d.png                           # 생성된 3D PCA 산점도
├── cluster_interactive.html                 # 생성된 인터랙티브 웹 리포트
└── README.md                                # 프로그램 안내 설명서 (본 파일)
```

---

## 🚀 빠른 시작 가이드

### 1. 패키지 설치 (선택 사항)
본 프로그램은 `numpy`와 `matplotlib`만 있으면 100% 자립 실행되며, 필요 시 아래 명령으로 추가 라이브러리를 설치할 수 있습니다:
```bash
pip install -r requirements.txt
```

### 2. 샘플 논문 PDF 생성 (최초 1회)
이미 `papers/` 폴더에 10편의 논문이 생성되어 있으며, 필요 시 언제든지 다시 생성할 수 있습니다:
```bash
python prepare_sample_papers.py
```

### 3. CLI 프로그램 실행 (핵심)
#### 기본 실행 (대화형 모드로 K값 입력 받음)
```bash
python paper_clustering.py
```

#### 클러스터 개수 K를 직접 지정하여 실행 (예: K=4)
```bash
python paper_clustering.py -k 4
```

#### 시각화 결과 파일 즉시 열기 (`--open`)
```bash
python paper_clustering.py -k 4 --open
```

#### CLI 주요 옵션 안내
- `-k`, `--clusters`: 생성할 클러스터 개수 (예: `-k 3`, `-k 4`)
- `-d`, `--dir`: PDF 논문 폴더 경로 (기본값: `papers`)
- `-m`, `--mode`: 임베딩 생성 방식 (`auto`, `tfidf`, `openai`)
- `--vis`: 시각화 생성 포맷 (`2d`, `3d`, `html`, `all`, `none`)
- `--open`: 생성 완료 후 이미지/HTML을 OS 기본 뷰어로 자동 오픈

---

## 💻 인터랙티브 웹 대시보드 실행

웹 브라우저에서 K값을 슬라이더로 조절하고 3D 차트를 마우스로 회전해보고 싶다면 웹 대시보드를 실행하세요:

```bash
python paper_clustering_web.py
```
- 브라우저 주소: `http://localhost:8505` 접속
- 슬라이더로 K값(2~6)을 실시간 변경하고 `⚡ 재군집화 실행` 클릭
- 각 논문 카드를 클릭하여 초록(Abstract), 저자, 키워드 모달 확인
- 논문 간 코사인 유사도 히트맵 매트릭스 확인

---

## 📊 군집화 결과 예시 (K=4)

```text
############################################################################
 🎯 [군집화 결과 요약] 총 10편의 논문을 4개 클러스터로 분류 완료
############################################################################

┌──────────────────────────────────────────────────────────────────────────
│ 🏷️  [클러스터 #0] AI / Deep Learning (3편 포함)
│ 🔑 핵심 대표 키워드: learning, language, neural, models, transformer
├──────────────────────────────────────────────────────────────────────────
│  [1] 📄 제목: Attention Mechanisms and Transformer Architectures for Neural...
│       📁 파일: AI_01_Transformer_Language_Models.pdf
│       ✍️  저자: Alex Vaswani, Elena Cho, David Silver
│       💡 요약: This paper investigates self-attention mechanisms and multi-head...
│       📍 2D 좌표: PC1=-0.225, PC2=0.485
│  [2] 📄 제목: Deep Residual Learning and Convolutional Neural Networks for...
│       📁 파일: AI_02_Computer_Vision_Residual_Networks.pdf
│  [3] 📄 제목: Aligning Large Language Models with Reinforcement Learning...
│       📁 파일: AI_03_Reinforcement_Learning_Human_Feedback.pdf
└──────────────────────────────────────────────────────────────────────────

┌──────────────────────────────────────────────────────────────────────────
│ 🏷️  [클러스터 #1] Biomedical / Genomics (2편 포함)
│ 🔑 핵심 대표 키워드: tumor, crispr-cas9, sequencing, immunotherapy, editing
├──────────────────────────────────────────────────────────────────────────
│  [1] 📄 제목: Precision Genome Editing with CRISPR-Cas9: Therapeutic...
│       📁 파일: Bio_01_CRISPR_Cas9_Gene_Editing.pdf
│  [2] 📄 제목: Single-Cell RNA Sequencing Reveals Tumor Microenvironment...
│       📁 파일: Bio_02_Single_Cell_RNA_Cancer_Immunology.pdf
└──────────────────────────────────────────────────────────────────────────

┌──────────────────────────────────────────────────────────────────────────
│ 🏷️  [클러스터 #2] Blockchain / FinTech (3편 포함)
│ 🔑 핵심 대표 키워드: decentralized, blockchain, market, finance, price
├──────────────────────────────────────────────────────────────────────────
│  [1] 📄 제목: Decentralized Finance: Constant Product Automated Market...
│       📁 파일: FinTech_01_Automated_Market_Makers.pdf
│  [2] 📄 제목: Security and Scalability Analysis of Proof-of-Stake...
│       📁 파일: FinTech_02_Proof_of_Stake_Consensus.pdf
│  [3] 📄 제목: Limit Order Book Dynamics and Machine Learning in...
│       📁 파일: FinTech_03_Algorithmic_High_Frequency_Trading.pdf
└──────────────────────────────────────────────────────────────────────────

┌──────────────────────────────────────────────────────────────────────────
│ 🏷️  [클러스터 #3] Climate / Renewable Energy (2편 포함)
│ 🔑 핵심 대표 키워드: carbon, solar, emissions, ocean, conversion
├──────────────────────────────────────────────────────────────────────────
│  [1] 📄 제목: Advancements in Perovskite Solar Cells: Power Conversion...
│       📁 파일: Climate_01_Perovskite_Solar_Cells.pdf
│  [2] 📄 제목: Anthropogenic Carbon Sequestration and Deep Ocean Circulation...
│       📁 파일: Climate_02_Ocean_Circulation_Carbon_Capture.pdf
└──────────────────────────────────────────────────────────────────────────
```

---

## 🧪 단위 테스트 실행

파이프라인의 모든 구성 요소(PDF 파싱, 벡터라이저 정규화, K-Means 군집화, 코사인 유사도 대칭성, PCA 차원 축소, 시각화 생성)를 테스트합니다:

```bash
python test_clustering.py
```
```text
Ran 5 tests in 0.617s
OK
```
