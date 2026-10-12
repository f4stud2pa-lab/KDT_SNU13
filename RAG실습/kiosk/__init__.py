"""카페 키오스크 RAG 시스템."""
import os
from pathlib import Path

from .agent import KioskAgent
from .documents import build_documents
from .menu import Menu
from .retriever import HybridRetriever

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def create_agent(model: str | None = None) -> KioskAgent:
    from openai import OpenAI

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY 환경변수를 설정해 주세요. (예: export OPENAI_API_KEY=sk-...)")
    client = OpenAI()
    menu = Menu(DATA / "menu.json")
    docs = build_documents(menu, DATA / "store_info.json")
    retriever = HybridRetriever(docs, menu, client,
                                embed_model=os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
                                cache_dir=DATA / ".cache")
    return KioskAgent(menu, retriever, client, model=model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
