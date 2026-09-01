from typing import List, Dict, Any
from investigation.candidates import CANDIDATE_EVIDENCE_ACTIONS

def rank_candidate_evidence(context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Ranks candidate evidence actions using the conceptual heuristic formula:
    candidate_value = (expected_uncertainty_reduction * relevance * reliability) / acquisition_cost
    """
    ranked = []
    for cand in CANDIDATE_EVIDENCE_ACTIONS:
        val = (cand["expected_uncertainty_reduction"] * cand["relevance"] * cand["reliability"]) / cand["acquisition_cost"]
        item = dict(cand)
        item["score"] = round(val, 4)
        ranked.append(item)

    # Sort descending by score
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked
