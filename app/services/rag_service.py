import os
import sys

# Ensure src/ modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.config import Config
from src.rag_engine import build_engine, RagEngine

class RAGServiceWrapper:
    def __init__(self):
        self.engine: RagEngine | None = None
        self.status = None

    def _get_engine(self) -> RagEngine:
        if self.engine is None:
            config = Config.from_env()
            self.engine, self.status = build_engine(config)
        return self.engine

    def query(self, question: str) -> dict:
        engine = self._get_engine()
        ans = engine.answer(question)

        # If LLM failed, display the caught exception message
        final_answer = ans.text
        if ans.error:
            final_answer = f"[LLM ERROR: {ans.error}] {ans.text}"

        return {
            "question": question,
            "answer": final_answer,
            "citations": ans.citations,
            "warnings": ans.warnings,
            "language": ans.language
        }

rag_service = RAGServiceWrapper()