from typing import List, Dict, Any

CANDIDATE_EVIDENCE_ACTIONS = [
    {
        "id": "vibration_sample_10s",
        "label": "10-Second Vibration Sample",
        "description": "Collect rolling 10-second vibration telemetry window from bearing accelerometer.",
        "expected_uncertainty_reduction": 0.45,
        "relevance": 0.90,
        "reliability": 0.95,
        "acquisition_cost": 1.0,
        "type": "telemetry"
    },
    {
        "id": "high_res_neck_photo",
        "label": "High-Resolution Neck Angle Photo",
        "description": "Capture secondary close-up optical image focused on bottle neck stress ring.",
        "expected_uncertainty_reduction": 0.35,
        "relevance": 0.75,
        "reliability": 0.85,
        "acquisition_cost": 1.2,
        "type": "optical"
    },
    {
        "id": "sop_manual_retrieval",
        "label": "Line SOP Maintenance Manual Retrieval",
        "description": "Fetch manufacturer Standard Operating Procedure section for conveyor glass handling.",
        "expected_uncertainty_reduction": 0.20,
        "relevance": 0.50,
        "reliability": 0.80,
        "acquisition_cost": 0.5,
        "type": "document"
    }
]
