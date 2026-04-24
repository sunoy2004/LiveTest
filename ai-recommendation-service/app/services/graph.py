from __future__ import annotations

import logging
import threading
from typing import Any

import networkx as nx

log = logging.getLogger(__name__)


def _norm_tags(items: list[str] | None) -> set[str]:
    out: set[str] = set()
    if not items:
        return out
    for x in items:
        if isinstance(x, str) and x.strip():
            out.add(x.strip().lower())
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return round(inter / union, 4) if union else 0.0


class GraphStore:
    """
    In-memory graph: mentee user_id → mentor user_id edges weighted by goal/expertise overlap.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._g: nx.DiGraph = nx.DiGraph()

    def hydrate_from_snapshot(self, snapshot: dict[str, Any]) -> None:
        mentors = snapshot.get("mentors") or []
        mentees = snapshot.get("mentees") or []
        with self._lock:
            self._g.clear()
            for m in mentors:
                uid = str(m.get("user_id", ""))
                if not uid:
                    continue
                tags = _norm_tags(m.get("expertise_areas"))
                self._g.add_node(uid, role="mentor", tags=tags)
            for me in mentees:
                uid = str(me.get("user_id", ""))
                if not uid:
                    continue
                tags = _norm_tags(me.get("learning_goals"))
                self._g.add_node(uid, role="mentee", tags=tags)
            for me in mentees:
                mid = str(me.get("user_id", ""))
                if mid not in self._g:
                    continue
                mtags: set[str] = self._g.nodes[mid].get("tags", set())
                for mo in mentors:
                    hid = str(mo.get("user_id", ""))
                    if hid not in self._g:
                        continue
                    htags: set[str] = self._g.nodes[hid].get("tags", set())
                    w = _jaccard(mtags, htags)
                    self._g.add_edge(mid, hid, weight=w)
        log.info("graph hydrated: %d nodes", self._g.number_of_nodes())

    def bump_edge(self, *, mentee_user_id: str, mentor_user_id: str, delta: float) -> None:
        with self._lock:
            if not self._g.has_edge(mentee_user_id, mentor_user_id):
                if mentee_user_id in self._g and mentor_user_id in self._g:
                    w = _jaccard(
                        self._g.nodes[mentee_user_id].get("tags", set()),
                        self._g.nodes[mentor_user_id].get("tags", set()),
                    )
                    self._g.add_edge(mentee_user_id, mentor_user_id, weight=w)
                else:
                    return
            w = float(self._g[mentee_user_id][mentor_user_id].get("weight", 0.0))
            w2 = min(1.0, max(0.0, w + delta))
            self._g[mentee_user_id][mentor_user_id]["weight"] = round(w2, 4)

    def recommend(self, *, user_id: str, limit: int) -> list[dict]:
        with self._lock:
            if user_id not in self._g:
                raise KeyError(user_id)
            if self._g.nodes[user_id].get("role") != "mentee":
                raise KeyError(user_id)
            edges = list(self._g.out_edges(user_id, data=True))
        ranked = sorted(edges, key=lambda e: float(e[2].get("weight", 0.0)), reverse=True)
        out = []
        for _, mentor_uid, data in ranked[:limit]:
            out.append({"mentor_id": mentor_uid, "score": float(data.get("weight", 0.0))})
        return out


graph_store = GraphStore()
