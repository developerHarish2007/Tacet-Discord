from typing import Dict, Any, Optional

def evaluate_stage_b_negotiation(
    agrees_with_perception: bool,
    mean_confidence: float,
    match_info: Optional[dict],
    similarity_score: float
) -> Dict[str, Any]:
    """
    Stage B Negotiation Step:
    When Perception and Correlation disagree (agrees_with_perception is False),
    evaluates whether Memory Agent's historical diagnosis breaks the tie.
    """
    if agrees_with_perception:
        return {
            "negotiation_needed": False,
            "sides_with": "consensus",
            "tiebreaker_summary": "Perception and Correlation are in agreement; no tiebreaker required."
        }

    if not match_info or similarity_score < 0.30:
        return {
            "negotiation_needed": True,
            "sides_with": "neutral",
            "tiebreaker_summary": "Perception and Correlation disagree, but no relevant Memory match exists to break tie."
        }

    diagnosis = match_info.get("confirmed_diagnosis", "").lower()
    
    # Keywords indicating a real defect vs healthy baseline
    defect_keywords = ["scratch", "fracture", "crack", "chip", "defect", "wear", "jam", "shock"]
    normal_keywords = ["normal", "clean", "baseline", "no anomaly", "pass"]

    has_defect_keyword = any(kw in diagnosis for kw in defect_keywords)
    has_normal_keyword = any(kw in diagnosis for kw in normal_keywords)

    if has_defect_keyword and not has_normal_keyword:
        return {
            "negotiation_needed": True,
            "sides_with": "perception",
            "tiebreaker_summary": (
                f"Negotiation Result: Memory match (ID #{match_info.get('id')}, sim: {similarity_score:.2f}) "
                f"confirms historical defect diagnosis ('{match_info.get('confirmed_diagnosis')}'), siding with Perception visual model."
            )
        }
    elif has_normal_keyword:
        return {
            "negotiation_needed": True,
            "sides_with": "correlation",
            "tiebreaker_summary": (
                f"Negotiation Result: Memory match (ID #{match_info.get('id')}, sim: {similarity_score:.2f}) "
                f"confirms healthy operation ('{match_info.get('confirmed_diagnosis')}'), siding with Correlation vibration telemetry."
            )
        }

    return {
        "negotiation_needed": True,
        "sides_with": "neutral",
        "tiebreaker_summary": f"Negotiation Result: Memory match '{match_info.get('confirmed_diagnosis')}' neutral."
    }
