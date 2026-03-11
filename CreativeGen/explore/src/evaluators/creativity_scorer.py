#!/usr/bin/env python3
"""
Creativity Scorer - Code Similarity Based Evaluation
"""

import os
from typing import List, Dict, Optional, Tuple
import numpy as np
from openai import OpenAI


class CreativityScorer:

    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        """

        Args:
        """
        self.embedding_model = embedding_model
        self.client = OpenAI(api_key=os.getenv("MODEL_API_KEY"))

    def get_code_embedding(self, code: str) -> Optional[np.ndarray]:

        try:
            response = self.client.embeddings.create(
                input=code,
                model=self.embedding_model
            )
            embedding = np.array(response.data[0].embedding)
            return embedding
        except Exception as e:
            print(f"      ⚠️ Embedding API error: {str(e)}")
            return None

    def compute_code_similarity(self, code1: str, code2: str) -> Optional[float]:
  
        if not code1 or not code2:
            return None

        emb1 = self.get_code_embedding(code1)
        emb2 = self.get_code_embedding(code2)

        if emb1 is None or emb2 is None:
            return None

        # Compute cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return None

        similarity = dot_product / (norm1 * norm2)

        similarity = float(np.clip(similarity, 0.0, 1.0))

        return similarity

    def calculate_creativity_score(self, similarity: float) -> float:
   
  
        creativity_score = 100.0 * ((1.0 - similarity) ** 0.5)


        return creativity_score

    def evaluate_evolution(self, evolution_data: List[Dict]) -> Dict:

        baseline_code = None
        for evolution in evolution_data:
            if evolution['level'] == 0:
                baseline_code = evolution.get('solution')
                break

        if not baseline_code:
            return {
                'level_scores': {},
                'average_overall_score': 0.0,
                'max_overall_score': 0.0,
                'error': 'No baseline code (Level 0) found'
            }

        level_scores = {}
        all_overall_scores = []

        # Iterate levels >= 1
        for evolution in evolution_data:
            level = evolution['level']

            if level == 0:
                continue  # Skip baseline

            # Get code and success status for this level
            code = evolution.get('solution')
            success = evolution.get('success', False)

            # pass@1
            pass_at_1 = 1 if success else 0

            # If failed, record zero score
            if not success or not code:
                level_scores[str(level)] = {
                    'pass@1': pass_at_1,
                    'similarity': None,
                    'creativity': 0.0,
                    'overall': 0.0
                }
                all_overall_scores.append(0.0)
                continue

            # Compute similarity
            similarity = self.compute_code_similarity(baseline_code, code)

            if similarity is None:
                # Similarity computation failed; record zero
                level_scores[str(level)] = {
                    'pass@1': pass_at_1,
                    'similarity': None,
                    'creativity': 0.0,
                    'overall': 0.0,
                    'error': 'Similarity computation failed'
                }
                all_overall_scores.append(0.0)
                continue

            # Compute creativity score
            creativity = self.calculate_creativity_score(similarity)

            # Overall score = pass@1 × creativity
            overall_score = pass_at_1 * creativity

            level_scores[str(level)] = {
                'pass@1': pass_at_1,
                'similarity': round(similarity, 4),
                'creativity': round(creativity, 2),
                'overall': round(overall_score, 2)
            }

            all_overall_scores.append(overall_score)

        # Compute average and max
        average_overall_score = sum(all_overall_scores) / len(all_overall_scores) if all_overall_scores else 0.0
        max_overall_score = max(all_overall_scores) if all_overall_scores else 0.0

        return {
            'level_scores': level_scores,
            'average_overall_score': round(average_overall_score, 2),
            'max_overall_score': round(max_overall_score, 2)
        }
