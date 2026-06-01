import json
import sqlite3
import numpy as np
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"

try:
    from sentence_transformers import SentenceTransformer

    _model = None

    def get_model():
        global _model
        if _model is None:
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        return _model

    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class VectorStore:
    def __init__(self, db_path: Optional[str] = None, json_path: Optional[str] = None):
        self.db_path = db_path or str(DATA_DIR / "novafi.db")
        self.json_path = json_path or str(DATA_DIR / "novafi_dataset.json")
        self._embeddings = None
        self._email_texts = None
        self._email_ids = None

    def load_emails(self) -> tuple[list[str], list[int]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, from_name, to_name, subject, body FROM emails ORDER BY id")
        rows = c.fetchall()
        conn.close()

        texts = []
        ids = []
        for eid, frm, to, subj, body in rows:
            text = f"From: {frm} To: {to} Subject: {subj} Body: {body[:2000]}"
            texts.append(text)
            ids.append(eid)
        return texts, ids

    def build_embeddings(self):
        if not EMBEDDINGS_AVAILABLE:
            raise RuntimeError("sentence-transformers not installed")
        texts, ids = self.load_emails()
        model = get_model()
        self._email_texts = texts
        self._email_ids = ids
        self._embeddings = model.encode(texts, show_progress_bar=True)
        return self

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        return self._keyword_search(query, top_k)

    def _vector_search(self, query: str, top_k: int = 10) -> list[dict]:
        if self._embeddings is None:
            return self._keyword_search(query, top_k)
        model = get_model()
        query_vec = model.encode([query])[0]

        scores = []
        for i, emb in enumerate(self._embeddings):
            sim = float(np.dot(query_vec, emb) / (np.linalg.norm(query_vec) * np.linalg.norm(emb) + 1e-10))
            scores.append((i, sim))

        scores.sort(key=lambda x: x[1], reverse=True)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        results = []
        for idx, score in scores[:top_k]:
            eid = self._email_ids[idx]
            c.execute(
                "SELECT id, thread_id, from_name, from_addr, to_name, to_addr, cc, subject, body, timestamp, department, sensitivity "
                "FROM emails WHERE id = ?",
                (eid,),
            )
            row = c.fetchone()
            if row:
                results.append({
                    "id": row[0],
                    "thread_id": row[1],
                    "from_name": row[2],
                    "from_addr": row[3],
                    "to_name": row[4],
                    "to_addr": row[5],
                    "cc": row[6],
                    "subject": row[7],
                    "body": row[8][:1500],
                    "timestamp": row[9],
                    "department": row[10],
                    "sensitivity": row[11],
                    "relevance_score": round(score, 4),
                })

        conn.close()
        return results

    def _keyword_search(self, query: str, top_k: int = 10) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        terms = query.lower().split()
        results = []

        c.execute(
            "SELECT id, thread_id, from_name, from_addr, to_name, to_addr, cc, subject, body, timestamp, department, sensitivity "
            "FROM emails ORDER BY id"
        )
        all_rows = c.fetchall()

        scored = []
        for row in all_rows:
            text = f"{row[2]} {row[4]} {row[7]} {row[8]}".lower()
            score = sum(1 for t in terms if t in text)
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda x: x[0], reverse=True)

        for score, row in scored[:top_k]:
            results.append({
                "id": row[0],
                "thread_id": row[1],
                "from_name": row[2],
                "from_addr": row[3],
                "to_name": row[4],
                "to_addr": row[5],
                "cc": row[6],
                "subject": row[7],
                "body": row[8][:1500],
                "timestamp": row[9],
                "department": row[10],
                "sensitivity": row[11],
                "relevance_score": score,
            })

        conn.close()
        return results
