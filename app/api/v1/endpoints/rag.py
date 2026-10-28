import sys
import os

# Ensure src/ modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.rag_engine import RAGEngine  # Import teammate's engine class

class RAGServiceWrapper:
    def __init__(self):
        self.engine = None

    def initialize_engine(self):
        if self.engine is None:
            # Initializes vector store and Gemini client from teammate's code
            self.engine = RAGEngine()

    def query(self, question: str) -> dict:
        self.initialize_engine()
        # Call teammate's rag_engine process method
        result = self.engine.run(question)
        
        return {
            "question": question,
            "answer": result.get("answer", ""),
            "evidence": result.get("evidence", []),
            "sources": result.get("sources", [])
        }

rag_service = RAGServiceWrapper()