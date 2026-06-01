import json
import sqlite3
import threading
import numpy as np
from pathlib import Path
from typing import Optional
import sys

DATA_DIR = Path(__file__).parent.parent / "data"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"
IDS_PATH = DATA_DIR / "embedding_ids.npy"
EMBEDDING_DIM = 384

try:
    from sentence_transformers import SentenceTransformer
    _sbert_available = True
except ImportError:
    _sbert_available = False

_model = None
_model_lock = threading.Lock()

def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


class VectorStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DATA_DIR / "novafi.db")
        self._embeddings: Optional[np.ndarray] = None
        self._email_ids: Optional[list[int]] = None
        self._email_texts: Optional[list[str]] = None
        self._ready = False
        self._loading = False
        if _sbert_available and EMBEDDINGS_PATH.exists() and IDS_PATH.exists():
            try:
                arr = np.load(EMBEDDINGS_PATH)
                if arr.shape[1] == EMBEDDING_DIM:
                    self._embeddings = arr
                    self._email_ids = list(np.load(IDS_PATH))
                    self._email_texts, _ = self.load_emails()
                    self._ready = True
            except Exception:
                pass

    def load_emails(self) -> tuple[list[str], list[int]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, from_name, to_name, subject, body FROM emails ORDER BY id")
        rows = c.fetchall()
        conn.close()
        texts = []
        ids = []
        for eid, frm, to, subj, body in rows:
            texts.append(f"From: {frm} To: {to} Subject: {subj} Body: {body[:2000]}")
            ids.append(eid)
        return texts, ids

    def ensure_embeddings(self):
        if self._ready:
            return
        if not _sbert_available:
            return

        if EMBEDDINGS_PATH.exists() and IDS_PATH.exists():
            self._embeddings = np.load(EMBEDDINGS_PATH)
            self._email_ids = list(np.load(IDS_PATH))
            self._email_texts, _ = self.load_emails()
            self._ready = True
            return

        self._loading = True
        texts, ids = self.load_emails()
        model = _get_model()
        self._email_texts = texts
        self._email_ids = ids
        self._embeddings = model.encode(texts, show_progress_bar=False)
        np.save(EMBEDDINGS_PATH, self._embeddings)
        np.save(IDS_PATH, np.array(ids))
        self._ready = True
        self._loading = False

    def build_async(self):
        if self._ready or self._loading or not _sbert_available:
            return
        self._loading = True
        t = threading.Thread(target=self.ensure_embeddings, daemon=True)
        t.start()

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        if self._ready and _sbert_available:
            return self._vector_search(query, top_k)
        return self._keyword_search(query, top_k)

    def _vector_search(self, query: str, top_k: int = 10) -> list[dict]:
        model = _get_model()
        qv = model.encode([query])[0]
        dots = np.dot(self._embeddings, qv)
        norms = np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(qv) + 1e-10
        scores = dots / norms
        top_idx = np.argsort(scores)[-top_k:][::-1]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        results = []
        seen = set()
        for idx in top_idx:
            eid = int(self._email_ids[idx])
            c.execute(
                "SELECT id, thread_id, from_name, from_addr, to_name, to_addr, cc, subject, body, timestamp, department, sensitivity "
                "FROM emails WHERE id = ?", (eid,)
            )
            row = c.fetchone()
            if row and row[1] not in seen:
                seen.add(row[1])
                results.append(self._row_to_dict(row, float(scores[int(idx)])))
        conn.close()
        return results

    def _keyword_search(self, query: str, top_k: int = 10) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        terms = query.lower().split()
        c.execute(
            "SELECT id, thread_id, from_name, from_addr, to_name, to_addr, cc, subject, body, timestamp, department, sensitivity "
            "FROM emails ORDER BY id"
        )
        scored = []
        seen_threads = set()
        for row in c.fetchall():
            text = f"{row[2]} {row[4]} {row[7]} {row[8]}".lower()
            score = sum(1 for t in terms if t in text)
            if score > 0 and row[1] not in seen_threads:
                seen_threads.add(row[1])
                scored.append((score, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [self._row_to_dict(r, s) for s, r in scored[:top_k]]
        conn.close()
        return results

    def _row_to_dict(self, row, score: float) -> dict:
        return {
            "id": row[0], "thread_id": row[1],
            "from_name": row[2], "from_addr": row[3],
            "to_name": row[4], "to_addr": row[5],
            "cc": row[6], "subject": row[7],
            "body": row[8][:1500],
            "timestamp": row[9], "department": row[10],
            "sensitivity": row[11],
            "relevance_score": round(score, 4),
        }
