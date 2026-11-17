"""
RIT-Sync Vision - 1:N Face Matcher
Author: Paul Bryton Raj (AI & System Lead)

Performs 1:N open-set cosine similarity matching between a query face embedding
and a list of enrolled student templates.
"""

from typing import List, Tuple, Optional
import numpy as np
from shared.schemas import EnrolledTemplate


class MatchCandidate:
    def __init__(self, student_id: str, student_name: str, similarity: float):
        self.student_id = student_id
        self.student_name = student_name
        self.similarity = round(float(similarity), 4)


class FaceMatcher:
    """
    Computes cosine similarity against enrolled templates and returns top matches.
    """

    def find_top_matches(
        self,
        query_embedding: List[float],
        enrolled_templates: List[EnrolledTemplate],
        top_k: int = 2,
    ) -> List[MatchCandidate]:
        """
        :param query_embedding: 128-d L2 normalized vector
        :param enrolled_templates: List of enrolled templates for the class
        :param top_k: Number of highest matches to return
        :return: List of MatchCandidate sorted descending by similarity
        """
        if not enrolled_templates or not query_embedding:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
        q_vec = q_vec / q_norm

        candidates: List[MatchCandidate] = []

        for template in enrolled_templates:
            t_vec = np.array(template.embedding, dtype=np.float32)
            t_norm = np.linalg.norm(t_vec)
            if t_norm == 0:
                continue
            t_vec = t_vec / t_norm

            # Cosine similarity is dot product of L2 normalized vectors
            sim = float(np.dot(q_vec, t_vec))
            # Clip to [0.0, 1.0] for stability
            sim = max(0.0, min(1.0, sim))

            candidates.append(
                MatchCandidate(
                    student_id=template.student_id,
                    student_name=template.student_name,
                    similarity=sim,
                )
            )

        # Sort descending by similarity
        candidates.sort(key=lambda c: c.similarity, reverse=True)
        return candidates[:top_k]
