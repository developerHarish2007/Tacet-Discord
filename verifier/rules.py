from typing import Dict, Any, Tuple, Optional

def evaluate_stage_a_rules(
    mean_confidence: float,
    variance: float,
    agrees_with_perception: bool,
    sensor_anomaly: bool,
    similarity_score: float,
    has_match: bool
) -> Tuple[int, str]:
    """
    Stage A Rule Engine: Enforces exact deterministic thresholds.
    Returns Tuple[tier (1, 2, or 3), reasoning_string]
    """
    is_high_confidence = mean_confidence >= 0.75
    is_consistent_variance = variance <= 0.15
    is_strong_match = has_match and (similarity_score >= 0.70)
    is_weak_match = has_match and (0.30 <= similarity_score < 0.70)
    no_match = not has_match or (similarity_score < 0.30)

    # 1. TIER 1 Checklist: All conditions must be strictly satisfied
    if is_high_confidence and is_consistent_variance and agrees_with_perception and is_strong_match:
        reasoning = (
            f"Tier 1 (Strong Confirmed Match): High visual confidence ({mean_confidence:.2f}), "
            f"low MC Dropout variance ({variance:.4f}), sensor agreement (True), "
            f"and strong memory match ({similarity_score:.2f})."
        )
        return 1, reasoning

    # 2. TIER 2 Downgrade Triggers (Any of these while evidence exists)
    if is_high_confidence and not agrees_with_perception:
        reasoning = (
            f"Tier 2 (Unconfirmed - Conflict Downgrade): Perception confident ({mean_confidence:.2f}) "
            f"but Correlation disagrees with sensor telemetry trend."
        )
        return 2, reasoning

    if not is_consistent_variance and (is_high_confidence or has_match):
        reasoning = (
            f"Tier 2 (Unconfirmed - Variance Downgrade): High MC Dropout variance ({variance:.4f} > 0.15) "
            f"indicates visual model stochastic inconsistency across forward passes."
        )
        return 2, reasoning

    if is_weak_match:
        reasoning = (
            f"Tier 2 (Unconfirmed - Partial Memory Match): Memory similarity ({similarity_score:.2f}) "
            f"is a weak/partial match (between 0.30 and 0.70). Labeling answer as tentative."
        )
        return 2, reasoning

    if is_high_confidence and is_consistent_variance and agrees_with_perception and no_match:
        reasoning = (
            f"Tier 2 (Unconfirmed - No Prior Incident Record): High visual confidence ({mean_confidence:.2f}) "
            f"and sensor agreement, but no prior senior-confirmed match in incident memory."
        )
        return 2, reasoning

    # 3. TIER 3: No Match & Low Confidence / High Variance / Nothing lines up
    if no_match and (not is_high_confidence or not is_consistent_variance):
        reasoning = (
            f"Tier 3 (No Confident Match - Redirection Required): Visual confidence low ({mean_confidence:.2f} < 0.75) "
            f"or variance high ({variance:.4f}), with no incident memory match. Redirection to senior technician."
        )
        return 3, reasoning

    # Default Tier 3 fallback
    return 3, f"Tier 3 (No Match): Multi-agent signals insufficient for confident ruling. (Confidence: {mean_confidence:.2f}, Sim: {similarity_score:.2f})."
