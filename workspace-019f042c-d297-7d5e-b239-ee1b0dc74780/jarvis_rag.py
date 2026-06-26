"""
JARVIS v4 - RAG System (Retrieval-Augmented Generation)
=======================================================
Document upload, text chunking, embeddings, and vector search.

Supports: PDF, TXT, DOCX, MD, PY, JS, HTML, CSS, JSON, CSV
Uses: ChromaDB for vector storage, sentence-transformers for embeddings
"""

import os
import re
import hashlib
import traceback
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from jarvis_core import BASE_DIR, speak, OWNER_NAME

# Directories
RAG_DIR = BASE_DIR / "rag"
DOCUMENTS_DIR = RAG_DIR / "documents"
CHROMA_DIR = RAG_DIR / "chroma_db"

for d in [RAG_DIR, DOCUMENTS_DIR, CHROMA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Try to import optional dependencies
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("[WARNING] chromadb not installed. RAG features will be disabled.")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("[WARNING] sentence-transformers not installed. RAG features will be disabled.")

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("[WARNING] PyPDF2 not installed. PDF uploads will not work.")

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("[WARNING] python-docx not installed. DOCX uploads will not work.")


# ============================================================
# TEXT CHUNKING
# ============================================================

class TextChunker:
    """Split documents into semantically meaningful chunks."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 128,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n\n",  # Paragraph breaks
            "\n\n",    # Section breaks
            "\n",      # Line breaks
            ". ",      # Sentences
            "! ",
            "? ",
            "; ",
            ", ",
            " ",       # Words
            "",
        ]

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []

        # Clean text
        text = self._clean_text(text)

        # If text fits in one chunk, return it
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Find the best end position
            end = min(start + self.chunk_size, len(text))

            if end < len(text):
                # Try to break at a separator
                best_break = end
                for sep in self.separators:
                    pos = text.rfind(sep, start, end)
                    if pos > start + self.chunk_size // 2:
                        best_break = pos + len(sep)
                        break
                end = best_break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start with overlap
            start = end - self.chunk_overlap
            if start >= end:
                start = end

        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        # Remove null bytes
        text = text.replace('\x00', '')
        return text.strip()


# ============================================================
# DOCUMENT PARSER
# ============================================================

class DocumentParser:
    """Parse various document formats into plain text."""

    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.py', '.js', '.jsx', '.ts', '.tsx',
        '.html', '.htm', '.css', '.json', '.csv', '.xml',
        '.yaml', '.yml', '.c', '.cpp', '.h', '.java', '.cs',
        '.go', '.rs', '.rb', '.php', '.swift', '.kt',
    }

    @classmethod
    def parse_file(cls, file_path: Path) -> Dict:
        """
        Parse a document file and return metadata + text content.
        Returns: {"filename", "extension", "text", "pages", "error"}
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        result = {
            "filename": path.name,
            "extension": ext,
            "text": "",
            "pages": 0,
            "error": None,
        }

        try:
            if ext == '.pdf':
                result.update(cls._parse_pdf(path))
            elif ext == '.docx':
                result.update(cls._parse_docx(path))
            elif ext in cls.SUPPORTED_EXTENSIONS or ext == '':
                result.update(cls._parse_text(path))
            else:
                result["error"] = f"Unsupported file type: {ext}"
        except Exception as e:
            result["error"] = f"Parse error: {str(e)}"

        return result

    @staticmethod
    def _parse_pdf(path: Path) -> Dict:
        """Parse PDF file."""
        if not PDF_AVAILABLE:
            return {"error": "PyPDF2 not installed. Install with: pip install PyPDF2"}

        text_parts = []
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {i+1} ---\n{page_text}")

        return {
            "text": "\n\n".join(text_parts),
            "pages": num_pages,
        }

    @staticmethod
    def _parse_docx(path: Path) -> Dict:
        """Parse Word document."""
        if not DOCX_AVAILABLE:
            return {"error": "python-docx not installed. Install with: pip install python-docx"}

        doc = docx.Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        return {
            "text": "\n\n".join(paragraphs),
            "pages": len(doc.sections),
        }

    @staticmethod
    def _parse_text(path: Path) -> Dict:
        """Parse plain text files."""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    text = f.read()
                return {"text": text, "pages": 1}
            except UnicodeDecodeError:
                continue

        return {"error": "Could not decode file with any supported encoding."}


# ============================================================
# VECTOR STORE (ChromaDB)
# ============================================================

class VectorStore:
    """ChromaDB-based vector store for document embeddings."""

    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.chunker = TextChunker()
        self._initialized = False
        self._init()

    def _init(self):
        """Initialize ChromaDB client and embedding model."""
        if not CHROMADB_AVAILABLE or not SENTENCE_TRANSFORMERS_AVAILABLE:
            print("[RAG] Vector store dependencies not available.")
            return

        try:
            # Initialize ChromaDB
            self.client = chromadb.Client(Settings(
                chroma_db_dir=str(CHROMA_DIR),
                anonymized_telemetry=False,
                persist_directory=str(CHROMA_DIR),
            ))

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="jarvis_documents",
                metadata={"hnsw:space": "cosine"}
            )

            # Initialize embedding model (lightweight, runs on CPU)
            print("[RAG] Loading embedding model...")
            self.embedding_model = SentenceTransformer(
                'all-MiniLM-L6-v2',
                device='cpu'
            )
            print("[RAG] Embedding model loaded.")

            self._initialized = True

        except Exception as e:
            print(f"[RAG ERROR] Failed to initialize vector store: {e}")

    def is_ready(self) -> bool:
        """Check if vector store is initialized and ready."""
        return self._initialized

    def _get_embedding(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts."""
        if not self.embedding_model:
            return []
        return self.embedding_model.encode(texts, show_progress_bar=False).tolist()

    def add_document(self, file_path: Path) -> Dict:
        """
        Parse, chunk, and add a document to the vector store.
        Returns: {"success", "chunks_added", "document_id", "error"}
        """
        if not self.is_ready():
            return {"success": False, "error": "Vector store not initialized"}

        # Parse document
        parse_result = DocumentParser.parse_file(file_path)
        if parse_result["error"]:
            return {"success": False, "error": parse_result["error"]}

        text = parse_result["text"]
        if not text.strip():
            return {"success": False, "error": "Document is empty"}

        # Generate document ID
        doc_id = hashlib.md5(
            f"{file_path.name}_{text[:100]}".encode()
        ).hexdigest()[:12]

        # Remove existing document if present
        self.delete_document(doc_id)

        # Chunk text
        chunks = self.chunker.chunk_text(text)
        if not chunks:
            return {"success": False, "error": "Could not chunk document"}

        # Generate embeddings and add to collection
        embeddings = self._get_embedding(chunks)
        chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{
            "doc_id": doc_id,
            "filename": parse_result["filename"],
            "chunk_index": i,
            "total_chunks": len(chunks),
            "source": str(file_path),
        } for i in range(len(chunks))]

        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        # Save file to documents directory
        dest = DOCUMENTS_DIR / file_path.name
        import shutil
        shutil.copy2(file_path, dest)

        return {
            "success": True,
            "chunks_added": len(chunks),
            "document_id": doc_id,
            "filename": parse_result["filename"],
        }

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        doc_filter: str = None
    ) -> List[Dict]:
        """
        Query the vector store for relevant chunks.
        Returns list of chunks with similarity scores.
        """
        if not self.is_ready():
            return []

        try:
            query_embedding = self._get_embedding([query_text])

            where_filter = None
            if doc_filter:
                where_filter = {"doc_id": doc_filter}

            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            chunks = []
            if results and results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    # Convert cosine distance to similarity score (0-100)
                    similarity = max(0, round((1 - distance) * 100, 1))

                    chunks.append({
                        "id": doc_id,
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "similarity": similarity,
                    })

            return chunks

        except Exception as e:
            print(f"[RAG QUERY ERROR] {e}")
            return []

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and all its chunks from the vector store."""
        if not self.is_ready():
            return False

        try:
            self.collection.delete(where={"doc_id": doc_id})
            return True
        except Exception as e:
            print(f"[RAG DELETE ERROR] {e}")
            return False

    def list_documents(self) -> List[Dict]:
        """List all documents in the vector store."""
        if not self.is_ready():
            return []

        try:
            results = self.collection.get(include=["metadatas"])
            if not results or not results["ids"]:
                return []

            # Group by document
            docs = {}
            for i, doc_id in enumerate(results["ids"]):
                meta = results["metadatas"][i]
                d_id = meta.get("doc_id", "unknown")
                if d_id not in docs:
                    docs[d_id] = {
                        "doc_id": d_id,
                        "filename": meta.get("filename", "Unknown"),
                        "total_chunks": meta.get("total_chunks", 0),
                    }

            return list(docs.values())

        except Exception as e:
            print(f"[RAG LIST ERROR] {e}")
            return []

    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        if not self.is_ready():
            return {"status": "not_initialized"}

        try:
            count = self.collection.count()
            docs = self.list_documents()
            return {
                "status": "ready",
                "total_chunks": count,
                "total_documents": len(docs),
                "documents": docs,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def clear_all(self):
        """Clear all documents from the vector store."""
        if not self.is_ready():
            return

        try:
            self.client.delete_collection("jarvis_documents")
            self.collection = self.client.get_or_create_collection(
                name="jarvis_documents",
                metadata={"hnsw:space": "cosine"}
            )
            # Clear documents directory
            for f in DOCUMENTS_DIR.iterdir():
                f.unlink()
        except Exception as e:
            print(f"[RAG CLEAR ERROR] {e}")


# ============================================================
# RAG ENGINE
# ============================================================

class RAGEngine:
    """
    High-level RAG interface for JARVIS.
    Combines vector search with AI-powered answer generation.
    """

    def __init__(self):
        self.vector_store = VectorStore()

    def is_ready(self) -> bool:
        return self.vector_store.is_ready()

    def upload_document(self, file_path: Path) -> Dict:
        """Upload and index a document."""
        result = self.vector_store.add_document(file_path)
        if result["success"]:
            speak(f"Document indexed: {result['chunks_added']} chunks from {result['filename']}.")
        return result

    def ask_document(
        self,
        query: str,
        doc_filter: str = None,
        n_chunks: int = 5
    ) -> Dict:
        """
        Ask a question about uploaded documents.
        Returns: {"answer", "sources", "context"}
        """
        if not self.is_ready():
            return {
                "answer": "RAG system is not available. Please install required dependencies.",
                "sources": [],
                "context": "",
            }

        # Retrieve relevant chunks
        chunks = self.vector_store.query(query, n_results=n_chunks, doc_filter=doc_filter)

        if not chunks:
            return {
                "answer": f"I couldn't find any relevant information in the documents for: '{query}'. Try uploading documents first or rephrasing your question.",
                "sources": [],
                "context": "",
            }

        # Build context from chunks
        context_parts = []
        sources = []

        for i, chunk in enumerate(chunks):
            context_parts.append(
                f"[Document: {chunk['metadata']['filename']}, "
                f"Chunk {chunk['metadata']['chunk_index']+1}/{chunk['metadata']['total_chunks']}]\n"
                f"{chunk['text']}"
            )
            sources.append({
                "filename": chunk["metadata"]["filename"],
                "similarity": chunk["similarity"],
                "text_preview": chunk["text"][:200] + "...",
            })

        context = "\n\n---\n\n".join(context_parts)

        return {
            "sources": sources,
            "context": context,
            "chunks": chunks,
        }

    def list_documents(self) -> List[Dict]:
        """List all indexed documents."""
        return self.vector_store.list_documents()

    def delete_document(self, doc_id: str) -> bool:
        """Delete an indexed document."""
        return self.vector_store.delete_document(doc_id)

    def get_stats(self) -> Dict:
        """Get RAG system statistics."""
        return self.vector_store.get_stats()

    def clear_all(self):
        """Clear all indexed documents."""
        self.vector_store.clear_all()


# ============================================================
# GLOBAL INSTANCE
# ============================================================

rag_engine = RAGEngine()


__all__ = [
    'RAGEngine', 'rag_engine',
    'VectorStore', 'TextChunker', 'DocumentParser',
]
