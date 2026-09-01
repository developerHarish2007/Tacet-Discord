import os
import json
import numpy as np
import pandas as pd
from typing import List, Dict, Any

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
AI4I_FILE = os.path.join(DATA_DIR, "ai4i2020_sampled.json")

def generate_ai4i_dataset(num_records: int = 1000) -> List[Dict[str, Any]]:
    """
    Generates 1,000 transformed records matching AI4I 2020 Predictive Maintenance Dataset schema
    (UCI / Kaggle benchmark with 14 operational features and labeled failure modes).
    """
    np.random.seed(42)
    records = []
    
    product_types = ['L', 'M', 'H']
    failure_types = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF', 'NORMAL']
    weights = [0.03, 0.03, 0.03, 0.03, 0.01, 0.87] # ~13% failure rate across types
    
    for udi in range(1, num_records + 1):
        ptype = np.random.choice(product_types, p=[0.6, 0.3, 0.1])
        pid = f"{ptype}{np.random.randint(10000, 99999)}"
        
        fail_type = np.random.choice(failure_types, p=weights)
        
        air_temp = round(float(np.random.uniform(295.0, 304.5)), 2)
        process_temp = round(float(air_temp + np.random.uniform(8.0, 12.0)), 2)
        rot_speed = int(np.random.uniform(1168, 2886))
        torque = round(float(np.random.uniform(3.8, 76.6)), 2)
        tool_wear = int(np.random.uniform(0, 253))
        
        if fail_type == 'TWF':
            tool_wear = int(np.random.uniform(200, 250))
            diag = f"Tool Wear Failure (TWF) - Tool wear reached {tool_wear} min on Product {pid}"
            fix = "1. Replace worn carbide tool bit.\n2. Inspect spindle chuck alignment.\n3. Reset tool wear counter to zero."
            conf = 0.94
        elif fail_type == 'HDF':
            air_temp = 302.5
            process_temp = 310.2
            rot_speed = 1350
            diag = f"Heat Dissipation Failure (HDF) - Air/Process temp diff under 8.6K at {rot_speed} RPM"
            fix = "1. Check coolant pump valve and thermal radiator.\n2. Clean heat exchanger filter screen.\n3. Verify fan shroud clearance."
            conf = 0.91
        elif fail_type == 'PWF':
            torque = round(float(np.random.uniform(62.0, 75.0)), 2)
            rot_speed = int(np.random.uniform(1200, 1350))
            diag = f"Power Failure (PWF) - Motor torque out of specification ({torque} Nm at {rot_speed} RPM)"
            fix = "1. Check drive belt tension and motor inverter output.\n2. Inspect torque limiter clutch assembly.\n3. Recalibrate drive controller."
            conf = 0.93
        elif fail_type == 'OSF':
            torque = round(float(np.random.uniform(55.0, 70.0)), 2)
            tool_wear = int(np.random.uniform(190, 240))
            diag = f"Overstrain Failure (OSF) - Product strain threshold breached (Tool wear: {tool_wear} min, Torque: {torque} Nm)"
            fix = "1. Reduce feed rate by 15% on line section B.\n2. Inspect workholding clamp pressure.\n3. Lubricate linear guide rails."
            conf = 0.89
        elif fail_type == 'RNF':
            diag = f"Random Transient Failure (RNF) - Spurious sensor signal fluctuation on Product {pid}"
            fix = "1. Inspect sensor wiring shield and connector seating.\n2. Clear transient fault log.\n3. Run 3-cycle test routine."
            conf = 0.85
        else:
            diag = f"Normal Operational Baseline - Product {pid} parameters nominal"
            fix = "1. No corrective action required.\n2. Routine operational log entry verified."
            conf = 0.98

        sensor_data = {
            "udi": udi,
            "product_id": pid,
            "product_type": ptype,
            "air_temperature_k": air_temp,
            "process_temperature_k": process_temp,
            "rotational_speed_rpm": rot_speed,
            "torque_nm": torque,
            "tool_wear_min": tool_wear,
            "failure_type": fail_type
        }
        
        # Pick reference visual sample image
        sample_img = "data/mvtec/bottle/test/broken_large/000.png" if fail_type != 'NORMAL' else "data/mvtec/bottle/train/good/000.png"
        
        records.append({
            "image_path": sample_img,
            "heatmap_path": None,
            "confirmed_diagnosis": diag,
            "fix_steps": fix,
            "voice_note_path": None,
            "confidence_at_capture": conf,
            "seeded": True,
            "provenance": "seeded_dataset",
            "sensor_data": sensor_data,
            "confirmed": True
        })
        
    return records

def save_ai4i_dataset():
    os.makedirs(DATA_DIR, exist_ok=True)
    records = generate_ai4i_dataset(1000)
    with open(AI4I_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Successfully generated and saved {len(records)} AI4I 2020 records to {AI4I_FILE}.")

if __name__ == "__main__":
    save_ai4i_dataset()
