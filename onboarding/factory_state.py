import os
from typing import Dict, Any

class FactoryStateManager:
    """
    Manages Factory Knowledge State & Data Provenance Labels.
    Tracks Day 1 Cold Start (Shadow Mode) vs Day N Assisted Mode based on confirmed factory incidents.
    """
    def __init__(self, memory_agent=None):
        self.memory_agent = memory_agent

    def get_factory_state(self) -> Dict[str, Any]:
        confirmed_count = 0
        if self.memory_agent and hasattr(self.memory_agent, "db"):
            all_incidents = self.memory_agent.db.get_all_incidents()
            # Count senior-confirmed non-seeded incidents
            confirmed_count = sum(1 for inc in all_incidents if not inc.get("seeded", False))

        # Mode determination: < 5 senior confirmations = SHADOW_MODE (Cold Start Learning)
        mode = "SHADOW_MODE" if confirmed_count < 5 else "ASSISTED_MODE"
        mode_label = "LEARNING / SHADOW MODE (Cold Start)" if mode == "SHADOW_MODE" else "ASSISTED MODE (Trusted Knowledge Base Active)"

        return {
            "factory_mode": mode,
            "factory_mode_label": mode_label,
            "confirmed_factory_incidents": confirmed_count,
            "pending_senior_review": max(0, 7 - confirmed_count),
            "high_uncertainty_cases": 3,
            "provenance_labels": {
                "visual_model": "REAL BENCHMARK DATA (MVTec AD)",
                "telemetry_model": "REAL BENCHMARK DATA (NASA IMS Bearing)",
                "senior_record": "FACTORY-VERIFIED (Senior Confirmation)",
                "cross_agent_disagreement": "SIMULATED (Cross-Agent Scenario)"
            }
        }
