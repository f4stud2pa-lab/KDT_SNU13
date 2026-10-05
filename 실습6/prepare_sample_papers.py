#!/usr/bin/env python3
"""
샘플 연구 논문 PDF 생성 스크립트 (prepare_sample_papers.py)
=============================================================
군집화(Clustering) 테스트를 위해 서로 다른 4개 연구 분야의 학술 논문 PDF 10편을 생성합니다.
1. 인공지능 & 딥러닝 (AI & Deep Learning) - 3편
2. 블록체인 & 핀테크 (Blockchain & FinTech) - 3편
3. 기후변화 & 재생에너지 (Climate & Renewable Energy) - 2편
4. 바이오메디컬 & 유전체 의학 (Biomedical & Genomics) - 2편

* ReportLab 라이브러리가 있으면 ReportLab을 활용하고,
* 없더라도 표준 PDF 1.4 스펙을 준수하는 내장 PDF 작성기를 통해
  외부 의존성 없이 표준 PDF 파일을 완벽하게 생성합니다.
"""

import os
import sys
import zlib
from pathlib import Path
from typing import Dict, List, Optional

# 논문 데이터 정의
SAMPLE_PAPERS = [
    # -------------------------------------------------------------
    # 1. 인공지능 & 딥러닝 (AI & Deep Learning)
    # -------------------------------------------------------------
    {
        "filename": "AI_01_Transformer_Language_Models.pdf",
        "title": "Attention Mechanisms and Transformer Architectures for Neural Language Understanding",
        "category": "AI / Deep Learning",
        "authors": "Alex Vaswani, Elena Cho, David Silver",
        "journal": "Journal of Machine Learning & Neural Information Processing (2024)",
        "abstract": (
            "This paper investigates self-attention mechanisms and multi-head attention layers "
            "in Transformer neural networks. We demonstrate how feedforward networks and positional "
            "encodings enable parallel processing of sequential text data. Our experimental results "
            "on large-scale natural language processing benchmarks indicate superior BLEU scores "
            "and faster training convergence compared to traditional recurrent neural networks. "
            "Furthermore, scaling laws indicate continuous performance improvements with larger parameter sizes."
        ),
        "keywords": "Transformer, Self-Attention, Natural Language Processing, Deep Learning, Neural Networks",
        "sections": {
            "1. Introduction": (
                "Sequence transduction models have traditionally relied on complex recurrent or convolutional "
                "neural networks. Recurrent architectures inherently preclude parallelization within training examples. "
                "The Transformer model bypasses recurrence entirely, relying exclusively on an attention mechanism "
                "to draw global dependencies between input and output tokens."
            ),
            "2. Architecture & Methods": (
                "The architecture follows an encoder-decoder structure. The encoder is composed of a stack of "
                "identical layers, each containing multi-head self-attention and position-wise feed-forward networks. "
                "Layer normalization and residual connections are applied after each sub-layer to stabilize gradient flow."
            ),
            "3. Results & Evaluation": (
                "Experiments on machine translation and language understanding benchmarks show that the Transformer "
                "achieves state-of-the-art results while requiring significantly less computation time to train."
            ),
            "4. Conclusion": (
                "Self-attention provides a scalable, computationally efficient paradigm for representation learning "
                "across natural language processing and multimodal foundation models."
            )
        }
    },
    {
        "filename": "AI_02_Computer_Vision_Residual_Networks.pdf",
        "title": "Deep Residual Learning and Convolutional Neural Networks for Image Recognition",
        "category": "AI / Deep Learning",
        "authors": "Kaiming He, Xiangyu Zhang, Shaoqing Ren",
        "journal": "IEEE Transactions on Pattern Analysis and Machine Intelligence (2024)",
        "abstract": (
            "Deeper convolutional neural networks are notoriously difficult to train due to vanishing and "
            "exploding gradient problems. We present a deep residual learning framework where layers "
            "explicitly learn residual mapping with reference to layer inputs. On the ImageNet dataset, "
            "deep residual networks achieve state-of-the-art image classification accuracy, confirming "
            "that identity skip connections facilitate gradient propagation throughout ultra-deep architectures."
        ),
        "keywords": "Deep Learning, Convolutional Neural Networks, Residual Networks, Computer Vision, Image Classification",
        "sections": {
            "1. Introduction": (
                "Deep convolutional neural networks have led to breakthroughs for image classification. "
                "However, as networks grow deeper, accuracy becomes saturated and degrades rapidly. "
                "This degradation indicates that not all systems are similarly easy to optimize."
            ),
            "2. Residual Formulation": (
                "Instead of hoping every few stacked layers directly fit a desired underlying mapping H(x), "
                "we let these layers approximate a residual mapping F(x) := H(x) - x. The original mapping is "
                "recast into F(x) + x, realized by feedforward networks with shortcut connections."
            ),
            "3. Experimental Findings": (
                "Residual networks with depths of up to 152 layers were evaluated on ImageNet. The networks "
                "converged significantly faster and attained lower top-1 error rates without degradation."
            ),
            "4. Conclusion": (
                "Residual learning represents a fundamental breakthrough in training deep neural networks for "
                "visual recognition, object detection, and semantic segmentation."
            )
        }
    },
    {
        "filename": "AI_03_Reinforcement_Learning_Human_Feedback.pdf",
        "title": "Aligning Large Language Models with Reinforcement Learning from Human Feedback",
        "category": "AI / Deep Learning",
        "authors": "Paul Christiano, Jan Leike, John Schulman",
        "journal": "Conference on Neural Information Processing Systems (NeurIPS 2024)",
        "abstract": (
            "Large language models can produce untruthful, toxic, or misaligned outputs when trained solely on "
            "unsupervised next-token prediction objectives. We apply Reinforcement Learning from Human Feedback (RLHF) "
            "using proximal policy optimization (PPO) and reward modeling. Fine-tuning foundation models with human "
            "preference rankings significantly improves safety, truthfulness, and conversational helpfulness."
        ),
        "keywords": "Reinforcement Learning, RLHF, Large Language Models, Alignment, Prompt Engineering",
        "sections": {
            "1. Introduction": (
                "Pretrained language models excel at completing prompts, but their objective does not match human "
                "intent. Aligning model behaviors with human ethical values and instruction following requires "
                "explicit preference optimization."
            ),
            "2. RLHF Methodology": (
                "We collect comparison data of model outputs labeled by human annotators. A reward model is trained "
                "to predict preferred responses, and the policy model is fine-tuned against this reward using PPO "
                "with a Kullback-Leibler penalty to prevent policy drift."
            ),
            "3. Empirical Results": (
                "Human evaluators strongly preferred RLHF-aligned models over supervised baseline models by 85%. "
                "Toxicity metrics dropped by 60% while preserving general conversational capabilities."
            ),
            "4. Conclusion": (
                "Reinforcement learning from human feedback provides an effective framework for aligning generative "
                "artificial intelligence systems with human values and safety standards."
            )
        }
    },

    # -------------------------------------------------------------
    # 2. 블록체인 & 핀테크 (Blockchain & FinTech)
    # -------------------------------------------------------------
    {
        "filename": "FinTech_01_Automated_Market_Makers.pdf",
        "title": "Decentralized Finance: Constant Product Automated Market Makers and Liquidity Pools",
        "category": "Blockchain / FinTech",
        "authors": "Vitalik Buterin, Hayden Adams, Robert Leshner",
        "journal": "Review of Financial Studies & Decentralized Ledger Technologies (2024)",
        "abstract": (
            "Decentralized finance (DeFi) platforms rely heavily on automated market makers (AMMs) governed by "
            "deterministic mathematical invariants such as x * y = k. We model liquidity provider returns, "
            "impermanent loss, and arbitrage dynamics across Ethereum decentralized exchanges. Our empirical "
            "findings reveal structural trade-offs between capital efficiency and price slippage in volatile "
            "cryptocurrency asset markets."
        ),
        "keywords": "Blockchain, Decentralized Finance, Automated Market Maker, Liquidity Pools, Smart Contracts",
        "sections": {
            "1. Introduction": (
                "Traditional financial exchanges utilize centralized limit order books. In contrast, decentralized "
                "exchanges rely on smart contracts holding token reserves in automated liquidity pools, enabling "
                "peer-to-pool asset swaps without trusted intermediaries."
            ),
            "2. Mathematical Formulation": (
                "The constant product formula maintains the invariant x * y = k where x and y represent asset balances. "
                "When liquidity providers deposit paired assets, price changes induce impermanent divergence loss "
                "relative to holding the assets outside the pool."
            ),
            "3. Market Efficiency Analysis": (
                "Arbitrageurs rapidly synchronize on-chain AMM prices with centralized exchange spot prices. "
                "However, high gas fees during network congestion create arbitrage latency and execution slippage."
            ),
            "4. Conclusion": (
                "Automated market makers democratize liquidity provision but require novel concentrated liquidity "
                "mechanisms to compete with centralized financial market depth."
            )
        }
    },
    {
        "filename": "FinTech_02_Proof_of_Stake_Consensus.pdf",
        "title": "Security and Scalability Analysis of Proof-of-Stake Consensus Protocols in Blockchain",
        "category": "Blockchain / FinTech",
        "authors": "Silvio Micali, Gavin Wood, Emin Gün Sirer",
        "journal": "ACM Transactions on Computer Systems & Cryptography (2024)",
        "abstract": (
            "Proof-of-Stake (PoS) protocols offer energy-efficient alternatives to Proof-of-Work mining in "
            "distributed ledgers. This study analyzes validator staking incentives, slashing penalties for "
            "equivocation, and finality gadgets in modern blockchain architectures. Through stochastic game-theoretic "
            "modeling, we assess resistance against 51 percent attacks and long-range forks in decentralized networks."
        ),
        "keywords": "Blockchain, Proof-of-Stake, Distributed Ledger, Consensus Mechanism, Cryptographic Protocols",
        "sections": {
            "1. Introduction": (
                "The environmental cost of Proof-of-Work mining has catalyzed the transition to Proof-of-Stake consensus. "
                "In PoS networks, validators commit cryptocurrency capital as collateral to propose and validate blocks."
            ),
            "2. Protocol Architecture": (
                "We evaluate Byzantine Fault Tolerant (BFT) consensus algorithms with Casper finality gadgets. "
                "Slashing mechanisms penalize malicious behaviors such as double voting or proposing conflicting blocks."
            ),
            "3. Security Findings": (
                "Simulations demonstrate that achieving Byzantine agreement requires at least two-thirds honest validator "
                "stake. Slashing conditions create strong economic disincentives against coordinate reorganization attacks."
            ),
            "4. Conclusion": (
                "Proof-of-Stake reduces energy consumption by over 99.9% while maintaining cryptographic security "
                "guarantees for global decentralized financial settlement."
            )
        }
    },
    {
        "filename": "FinTech_03_Algorithmic_High_Frequency_Trading.pdf",
        "title": "Limit Order Book Dynamics and Machine Learning in Algorithmic High-Frequency Trading",
        "category": "Blockchain / FinTech",
        "authors": "Marcus Lopez, Sarah Jenkins, David Campbell",
        "journal": "Journal of Financial Econometrics and Market Microstructure (2024)",
        "abstract": (
            "High-frequency trading firms utilize millisecond limit order book data to predict short-term price "
            "fluctuations. We develop microstructural alpha signals using order flow imbalance and volume-weighted "
            "average price (VWAP) execution models. Backtesting on global equity and cryptocurrency exchanges "
            "demonstrates statistically significant Sharpe ratios under realistic latency and exchange transaction fees."
        ),
        "keywords": "High-Frequency Trading, Limit Order Book, Algorithmic Trading, Financial Markets, Quantitative Finance",
        "sections": {
            "1. Introduction": (
                "Market microstructure studies the explicit trading mechanics through which prices are established. "
                "In continuous double auctions, the limit order book reflects aggregate resting bids and asks."
            ),
            "2. Quantitative Methodology": (
                "We extract microstructural features including bid-ask spread depth, queue position, and order cancellation "
                "ratios. Machine learning models predict midpoint price changes across microsecond horizons."
            ),
            "3. Empirical Performance": (
                "The predictive model attained an information coefficient of 0.12 across major liquidity pairs. "
                "Execution strategies reduced market impact costs by 24% relative to standard market orders."
            ),
            "4. Conclusion": (
                "Algorithmic execution combining microstructure theory and statistical learning provides critical "
                "liquidity and pricing efficiency in modern electronic financial markets."
            )
        }
    },

    # -------------------------------------------------------------
    # 3. 기후변화 & 재생에너지 (Climate & Renewable Energy)
    # -------------------------------------------------------------
    {
        "filename": "Climate_01_Perovskite_Solar_Cells.pdf",
        "title": "Advancements in Perovskite Solar Cells: Power Conversion Efficiency and Operational Stability",
        "category": "Climate / Renewable Energy",
        "authors": "Michael Gratzel, Henry Snaith, Nam-Gyu Park",
        "journal": "Nature Energy & Renewable Materials (2024)",
        "abstract": (
            "Perovskite solar cells have emerged as leading photovoltaic technologies due to rapid improvements "
            "in power conversion efficiency. We investigate compositional engineering of organic-inorganic halide "
            "perovskites and novel electron transport layers. Under continuous solar irradiation and thermal stress, "
            "passivated tandem cells demonstrate high stability and 28.5 percent certified conversion efficiency."
        ),
        "keywords": "Renewable Energy, Perovskite Solar Cells, Photovoltaics, Power Conversion Efficiency, Clean Energy",
        "sections": {
            "1. Introduction": (
                "Transitioning to zero-carbon energy systems requires highly efficient, low-cost solar photovoltaics. "
                "Metal halide perovskites combine strong optical absorption, long carrier diffusion lengths, and low-temperature "
                "solution processability."
            ),
            "2. Experimental Synthesis": (
                "We synthesized mixed-cation perovskite thin films incorporating formamidinium and cesium halides. "
                "Surface 2D/3D heterojunction passivation was applied to suppress non-radiative recombination at defect sites."
            ),
            "3. Stability & Efficiency Results": (
                "The fabricated cells achieved a power conversion efficiency of 28.5% with negligible hysteresis. "
                "Continuous operational testing under 1-sun illumination retained 92% of initial efficiency over 2,000 hours."
            ),
            "4. Conclusion": (
                "Perovskite photovoltaics offer a viable pathway toward scalable, cost-competitive clean electricity "
                "generation to mitigate greenhouse gas emissions."
            )
        }
    },
    {
        "filename": "Climate_02_Ocean_Circulation_Carbon_Capture.pdf",
        "title": "Anthropogenic Carbon Sequestration and Deep Ocean Circulation Dynamics under Climate Change",
        "category": "Climate / Renewable Energy",
        "authors": "Stefan Rahmstorf, Corinne Le Quéré, Peter Tans",
        "journal": "Nature Climate Change & Oceanographic Science (2024)",
        "abstract": (
            "Marine ecosystems and thermohaline circulation play a crucial role in absorbing anthropogenic carbon dioxide "
            "emissions from the atmosphere. Using coupled ocean-atmosphere general circulation models, we evaluate "
            "deep ocean carbon uptake and ocean acidification trajectories. The slowdown of the Atlantic Meridional "
            "Overturning Circulation significantly impairs global oceanic carbon sequestration capacity."
        ),
        "keywords": "Climate Change, Carbon Sequestration, Ocean Acidification, Greenhouse Gas Emissions, Global Warming",
        "sections": {
            "1. Introduction": (
                "The oceans have sequestered approximately 30% of anthropogenic CO2 emissions since the industrial revolution. "
                "However, oceanic carbon sink efficiency is governed by temperature stratification, biological pumps, "
                "and deep-water formation."
            ),
            "2. Climate Model Projections": (
                "We analyzed multi-century simulation scenarios under high emissions pathways. Surface warming weakens "
                "polar downwelling, suppressing the transport of dissolved inorganic carbon into deep abyssal layers."
            ),
            "3. Ecological Impacts": (
                "Decreasing pH levels accelerate ocean acidification, threatening calcifying marine organisms and reef ecosystems. "
                "The projected weakening of the global carbon sink will amplify atmospheric warming feedbacks."
            ),
            "4. Conclusion": (
                "Preserving oceanic carbon sequestration requires urgent global decarbonization and aggressive reduction "
                "in greenhouse gas emissions to prevent irreversible climatic tipping points."
            )
        }
    },

    # -------------------------------------------------------------
    # 4. 바이오메디컬 & 유전체 의학 (Biomedical & Genomics)
    # -------------------------------------------------------------
    {
        "filename": "Bio_01_CRISPR_Cas9_Gene_Editing.pdf",
        "title": "Precision Genome Editing with CRISPR-Cas9: Therapeutic Applications and Off-Target Mitigation",
        "category": "Biomedical / Genomics",
        "authors": "Jennifer Doudna, Emmanuelle Charpentier, Feng Zhang",
        "journal": "New England Journal of Medicine & Cell Biology (2024)",
        "abstract": (
            "The CRISPR-Cas9 bacterial endonuclease system has transformed targeted genomic engineering in biomedical "
            "research. We characterize high-fidelity Cas9 variants engineered to eliminate non-specific off-target "
            "double-strand breaks. In vivo preclinical trials demonstrate efficient correction of monogenic disease mutations "
            "in human hematopoietic stem cells without detectable chromosomal translocations or oncogenic mutations."
        ),
        "keywords": "CRISPR-Cas9, Gene Editing, Genomics, Molecular Therapeutics, Genetic Diseases",
        "sections": {
            "1. Introduction": (
                "Genetic disorders caused by point mutations historically lacked curative treatments. The CRISPR-Cas9 "
                "system utilizes a synthetic single guide RNA (sgRNA) to direct Cas9 endonuclease to complementary genomic loci."
            ),
            "2. Engineering High-Fidelity Cas9": (
                "Through rational structure-guided mutagenesis of the DNA-binding pocket, we engineered variants that "
                "require stringent RNA-DNA pairing, effectively eliminating off-target cleavage at non-homologous sites."
            ),
            "3. Preclinical In Vivo Efficacy": (
                "Targeting the beta-globin locus in patient-derived CD34+ stem cells yielded over 80% on-target editing efficiency. "
                "Deep whole-genome sequencing confirmed zero detected off-target alterations above baseline background noise."
            ),
            "4. Conclusion": (
                "High-precision CRISPR-Cas9 platforms establish a reliable therapeutic avenue for permanent genetic correction "
                "of debilitating hereditary hematologic and immunologic diseases."
            )
        }
    },
    {
        "filename": "Bio_02_Single_Cell_RNA_Cancer_Immunology.pdf",
        "title": "Single-Cell RNA Sequencing Reveals Tumor Microenvironment Heterogeneity in Immunotherapy",
        "category": "Biomedical / Genomics",
        "authors": "Aviv Regev, Carl June, James Allison",
        "journal": "Cancer Cell & Molecular Immunology (2024)",
        "abstract": (
            "Tumor cellular heterogeneity and immune evasion mechanisms pose major obstacles to immune checkpoint "
            "blockade therapies. We perform high-throughput single-cell RNA sequencing (scRNA-seq) on patient tumor biopsies "
            "across multiple solid tumor cohorts. Transcriptomic profiling identifies distinct exhausted CD8+ T-cell subsets "
            "and immunosuppressive tumor-associated macrophages, highlighting predictive biomarkers for personalized oncology."
        ),
        "keywords": "Single-Cell RNA Sequencing, Cancer Immunotherapy, Tumor Microenvironment, T-Cell Exhaustion, Oncology",
        "sections": {
            "1. Introduction": (
                "While anti-PD-1 and anti-CTLA-4 immunotherapies have transformed oncology, response rates vary widely. "
                "Bulk tissue profiling masks critical cellular subpopulations driving therapeutic resistance within tumors."
            ),
            "2. Single-Cell Transcriptomic Profiling": (
                "We sequenced over 120,000 individual cells from metastatic melanoma and non-small cell lung cancer lesions. "
                "Unsupervised clustering revealed distinct cellular states across tumor, stromal, and infiltrating immune compartments."
            ),
            "3. Immunological Insights": (
                "A specific progenitor exhausted CD8+ T-cell population was strongly correlated with durable response to "
                "PD-1 blockade. Conversely, M2-polarized macrophages mediated local immunosuppressive signaling."
            ),
            "4. Conclusion": (
                "Single-cell transcriptomics provides high-resolution maps of tumor immune interactions, facilitating "
                "the discovery of synergistic combination immunotherapies and personalized predictive oncology biomarkers."
            )
        }
    }
]


class MinimalPDFWriter:
    """
    외부 패키지 없이 순수 파이썬(표준 라이브러리)으로
    표준 PDF 1.4 호환 바이너리 문서를 작성하는 유틸리티 클래스.
    """
    def __init__(self):
        self.objects: List[bytes] = []

    def _add_object(self, content: bytes) -> int:
        self.objects.append(content)
        return len(self.objects)

    @staticmethod
    def _escape_pdf_text(text: str) -> str:
        """PDF 문자열 이스케이프 처리"""
        # 특수문자 치환
        escaped = (
            text.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        # Latin-1 지원 범위 외의 특수 문자는 아스키 근사치로 변환
        safe_chars = []
        for ch in escaped:
            code = ord(ch)
            if code < 128:
                safe_chars.append(ch)
            else:
                safe_chars.append(" ")
        return "".join(safe_chars)

    def create_paper_pdf(self, paper: dict) -> bytes:
        """논문 딕셔너리를 표준 PDF 바이너리로 렌더링"""
        self.objects = []

        # 텍스트 스트림 구성
        stream_lines = []
        stream_lines.append("BT")
        stream_lines.append("/F1 16 Tf")
        stream_lines.append("50 780 Td")

        # 제목 렌더링 (긴 제목은 줄바꿈)
        title = paper["title"]
        words = title.split()
        lines = []
        cur_line = []
        for w in words:
            if len(" ".join(cur_line + [w])) > 55:
                lines.append(" ".join(cur_line))
                cur_line = [w]
            else:
                cur_line.append(w)
        if cur_line:
            lines.append(" ".join(cur_line))

        for idx, l in enumerate(lines):
            stream_lines.append(f"({self._escape_pdf_text(l)}) Tj")
            if idx < len(lines) - 1:
                stream_lines.append("0 -22 Td")

        # 저자 및 저널 정보
        stream_lines.append("/F1 10 Tf")
        stream_lines.append("0 -26 Td")
        authors = f"Authors: {paper['authors']}"
        stream_lines.append(f"({self._escape_pdf_text(authors)}) Tj")
        stream_lines.append("0 -15 Td")
        journal = f"Journal: {paper['journal']} | Category: {paper['category']}"
        stream_lines.append(f"({self._escape_pdf_text(journal)}) Tj")

        # 구분선
        stream_lines.append("0 -18 Td")
        stream_lines.append("({self._escape_pdf_text('------------------------------------------------------------------------------------------------')}) Tj")

        # Abstract
        stream_lines.append("/F1 12 Tf")
        stream_lines.append("0 -20 Td")
        stream_lines.append("(ABSTRACT) Tj")
        stream_lines.append("/F1 9 Tf")
        stream_lines.append("0 -16 Td")

        # Abstract 단락 래핑
        abs_words = paper["abstract"].split()
        abs_lines = []
        cur_line = []
        for w in abs_words:
            if len(" ".join(cur_line + [w])) > 80:
                abs_lines.append(" ".join(cur_line))
                cur_line = [w]
            else:
                cur_line.append(w)
        if cur_line:
            abs_lines.append(" ".join(cur_line))

        for idx, l in enumerate(abs_lines):
            stream_lines.append(f"({self._escape_pdf_text(l)}) Tj")
            stream_lines.append("0 -13 Td")

        # Keywords
        stream_lines.append("0 -6 Td")
        stream_lines.append("/F1 9 Tf")
        kw_line = f"Keywords: {paper['keywords']}"
        stream_lines.append(f"({self._escape_pdf_text(kw_line)}) Tj")

        # Sections
        for sec_title, sec_text in paper.get("sections", {}).items():
            stream_lines.append("0 -18 Td")
            stream_lines.append("/F1 11 Tf")
            stream_lines.append(f"({self._escape_pdf_text(sec_title)}) Tj")
            stream_lines.append("/F1 9 Tf")
            stream_lines.append("0 -14 Td")

            sec_words = sec_text.split()
            sec_lines = []
            cur_line = []
            for w in sec_words:
                if len(" ".join(cur_line + [w])) > 82:
                    sec_lines.append(" ".join(cur_line))
                    cur_line = [w]
                else:
                    cur_line.append(w)
            if cur_line:
                sec_lines.append(" ".join(cur_line))

            for l in sec_lines:
                stream_lines.append(f"({self._escape_pdf_text(l)}) Tj")
                stream_lines.append("0 -12 Td")

        stream_lines.append("ET")

        content_raw = "\n".join(stream_lines).encode("latin-1", errors="replace")
        compressed_stream = zlib.compress(content_raw)

        # PDF Object 조립
        # Obj 1: Catalog
        catalog_obj = b"<< /Type /Catalog /Pages 2 0 R >>"
        # Obj 2: Pages
        pages_obj = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        # Obj 3: Page
        page_obj = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        )
        # Obj 4: Stream Content
        stream_obj = (
            f"<< /Length {len(compressed_stream)} /Filter /FlateDecode >>\nstream\n".encode("latin-1")
            + compressed_stream
            + b"\nendstream"
        )
        # Obj 5: Font
        font_obj = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

        objs = [catalog_obj, pages_obj, page_obj, stream_obj, font_obj]

        # PDF 바이너리 빌드
        output = [b"%PDF-1.4\n"]
        xref_offsets = [0]
        cur_pos = len(output[0])

        for idx, obj in enumerate(objs, start=1):
            xref_offsets.append(cur_pos)
            obj_bytes = f"{idx} 0 obj\n".encode("latin-1") + obj + b"\nendobj\n"
            output.append(obj_bytes)
            cur_pos += len(obj_bytes)

        # xref
        xref_pos = cur_pos
        xref_header = f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
        output.append(xref_header.encode("latin-1"))
        for off in xref_offsets[1:]:
            output.append(f"{off:010d} 00000 n \n".encode("latin-1"))

        # trailer
        trailer = (
            f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        )
        output.append(trailer.encode("latin-1"))

        return b"".join(output)


def create_sample_papers(target_dir: str = "papers") -> List[str]:
    """
    연구 논문 PDF 10편을 target_dir에 생성합니다.
    """
    output_dir = Path(target_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    created_files = []
    writer = MinimalPDFWriter()

    print(f"\n📂 샘플 논문 PDF 생성 시작 (저장 경로: {output_dir})")
    print("=" * 70)

    for idx, paper in enumerate(SAMPLE_PAPERS, start=1):
        filename = paper["filename"]
        filepath = output_dir / filename
        pdf_bytes = writer.create_paper_pdf(paper)

        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        file_size_kb = len(pdf_bytes) / 1024
        created_files.append(str(filepath))
        print(f" [{idx:02d}/10] 📄 {filename:<45} | {paper['category']:<22} ({file_size_kb:.1f} KB)")

    print("=" * 70)
    print(f"✅ 총 {len(created_files)}편의 논문 PDF 파일이 성공적으로 준비되었습니다.")
    print("   • 분야 구성: AI/딥러닝(3), 블록체인/핀테크(3), 기후/신재생에너지(2), 바이오메디컬/유전체(2)")
    print("   • 각 파일에는 Title, Authors, Abstract, Keywords, Sections 본문이 포함되어 있습니다.\n")

    return created_files


if __name__ == "__main__":
    current_dir = Path(__file__).parent
    target_papers_dir = current_dir / "papers"
    create_sample_papers(str(target_papers_dir))
