import sqlite3
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"


class VectorStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DATA_DIR / "novafi.db")

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        terms = [t.lower() for t in query.split() if len(t) > 2]
        if not terms:
            conn.close()
            return []

        c.execute(
            "SELECT id, thread_id, from_name, from_addr, to_name, to_addr, cc, subject, body, timestamp, department, sensitivity "
            "FROM emails ORDER BY id"
        )
        seen = set()
        scored = []
        for row in c.fetchall():
            if row[1] in seen:
                continue
            text = f"{row[2]} {row[4]} {row[7]} {row[8]}".lower()
            score = sum(term in text for term in terms)
            if score > 0:
                seen.add(row[1])
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
            "relevance_score": score,
        }
