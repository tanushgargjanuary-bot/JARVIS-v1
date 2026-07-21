"""
RAG engine — parse documents, chunk, embed with sentence-transformers,
and search with ChromaDB. Optional dependencies; degrades gracefully.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from jarvis.config import RAG_DIR, RAG_ENABLED

logger = logging.getLogger(__name__)

DOCS_DIR = RAG_DIR / "documents"
CHROMA_DIR = RAG_DIR / "chroma_db"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# Optional heavy deps
try:
    import chromadb; _CHROMA = True
except ImportError: _CHROMA = False

try:
    from sentence_transformers import SentenceTransformer; _ST = True
except ImportError: _ST = False

try:
    import PyPDF2; _PDF = True
except ImportError: _PDF = False

try:
    import docx; _DOCX = True
except ImportError: _DOCX = False


class RAGEngine:
    def __init__(self):
        self._ready = False
        if not RAG_ENABLED or not _CHROMA or not _ST:
            if RAG_ENABLED:
                logger.info("RAG deps not installed. pip install jarvis-assistant[rag]")
            return
        try:
            self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            self._collection = self._client.get_or_create_collection(
                name="jarvis_docs", metadata={"hnsw:space": "cosine"})
            self._model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
            self._ready = True
        except Exception as e:
            logger.error("RAG init failed: %s", e)

    @property
    def ready(self) -> bool:
        return self._ready

    def add_document(self, filepath: Path) -> dict:
        if not self._ready:
            return {"success": False, "error": "RAG not initialised"}
        text = self._parse(filepath)
        if not text.strip():
            return {"success": False, "error": "Empty or unsupported"}
        chunks = self._chunk(text)
        if not chunks:
            return {"success": False, "error": "No chunks"}
        doc_hash = hashlib.md5(f"{filepath.name}_{text[:100]}".encode()).hexdigest()
        ids = [f"{doc_hash}_{i}" for i in range(len(chunks))]
        embs = self._model.encode(chunks).tolist()
        metas = [{"source": filepath.name, "chunk": i} for i in range(len(chunks))]
        self._collection.add(ids=ids, embeddings=embs, documents=chunks, metadatas=metas)
        return {"success": True, "chunks": len(chunks)}

    def query(self, question: str, n: int = 3) -> list[dict]:
        if not self._ready: return []
        q_emb = self._model.encode([question]).tolist()
        res = self._collection.query(query_embeddings=q_emb, n_results=n,
                                      include=["documents", "metadatas", "distances"])
        out = []
        if res and res["documents"]:
            for docs, metas, dists in zip(res["documents"], res["metadatas"], res["distances"]):
                for doc, meta, dist in zip(docs, metas, dists):
                    out.append({"text": doc, "source": meta.get("source", "?"), "score": round(1 - dist, 4)})
        return out

    def _parse(self, path: Path) -> str:
        ext = path.suffix.lower()
        if ext == ".pdf" and _PDF:
            with open(path, "rb") as f:
                return "\n".join(p.extract_text() or "" for p in PyPDF2.PdfReader(f).pages)
        if ext == ".docx" and _DOCX:
            return "\n".join(p.text for p in docx.Document(str(path)).paragraphs if p.text.strip())
        if ext in {".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".csv", ".yaml", ".c", ".java", ".go"}:
            for enc in ("utf-8", "latin-1"):
                try: return path.read_text(encoding=enc)
                except UnicodeDecodeError: continue
        return ""

    def _chunk(self, text: str, size: int = 512, overlap: int = 128) -> list[str]:
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text: return []
        if len(text) <= size: return [text]
        chunks, start = [], 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                for sep in ["\n\n", ". ", "\n", " "]:
                    pos = text.rfind(sep, start + size // 2, end)
                    if pos > start: end = pos + len(sep); break
            chunk = text[start:end].strip()
            if chunk: chunks.append(chunk)
            start = end - overlap
            if start >= end: start = end
        return chunks
