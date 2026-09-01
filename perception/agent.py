import os
import uuid
import glob
import numpy as np
from PIL import Image
from perception.patchcore import PatchCoreAnomalyDetector

def apply_jet_colormap(matrix: np.ndarray) -> np.ndarray:
    """
    Applies Jet colormap (Blue=0.0 -> Cyan -> Green -> Yellow -> Red=1.0)
    to a 2D float array (0.0 to 1.0) using pure NumPy.
    Returns RGB uint8 array of shape (H, W, 3).
    """
    val = np.clip(matrix, 0.0, 1.0)
    r = np.clip(1.5 - np.abs(4.0 * val - 3.0), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(4.0 * val - 2.0), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(4.0 * val - 1.0), 0.0, 1.0)
    rgb = np.stack([r, g, b], axis=-1)
    return (rgb * 255.0).astype(np.uint8)

class PerceptionAgent:
    def __init__(self, data_dir: str = None, static_dir: str = None):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.data_dir = data_dir or os.path.join(base_dir, "data", "mvtec", "bottle")
        self.static_dir = static_dir or os.path.join(base_dir, "static")
        self.heatmap_dir = os.path.join(self.static_dir, "heatmaps")
        os.makedirs(self.heatmap_dir, exist_ok=True)
        
        self.detector = PatchCoreAnomalyDetector(mc_samples=20)
        self._initialize_memory_bank()

    def _initialize_memory_bank(self):
        train_good_dir = os.path.join(self.data_dir, "train", "good")
        if os.path.exists(train_good_dir):
            image_paths = glob.glob(os.path.join(train_good_dir, "*.png"))
            print(f"Fitting Perception Agent memory bank on {len(image_paths)} images from {train_good_dir}...")
            self.detector.fit_memory_bank(image_paths)
        else:
            print("No training images found; using default reference memory bank.")
            self.detector.fit_memory_bank([])

    def perceive(self, image_path: str) -> dict:
        """
        Runs perception analysis on given defect photo.
        Generates pixel-level anomaly heatmap and performs Monte Carlo Dropout.
        """
        results = self.detector.predict_with_mc_dropout(image_path)
        
        # Overlay heatmap onto original image
        heatmap_rel_path = self._render_and_save_heatmap(image_path, results["heatmap_matrix"])
        
        # mean_confidence represents visual prediction confidence (0-1)
        mean_conf = round(float(results["anomaly_score"]), 4)

        return {
            "anomaly_score": results["anomaly_score"],
            "mean_confidence": mean_conf,
            "variance": results["variance"],
            "heatmap_path": heatmap_rel_path,
            "status": "success"
        }

    def _render_and_save_heatmap(self, orig_image_path: str, heatmap_matrix: np.ndarray) -> str:
        """Overlays spatial anomaly heatmap on original image using PIL & Numpy"""
        if os.path.exists(orig_image_path):
            orig_pil = Image.open(orig_image_path).convert('RGB')
        else:
            orig_pil = Image.new('RGB', (224, 224), (30, 30, 35))

        w, h = orig_pil.size
        
        # Generate jet colormap image for heatmap
        heatmap_rgb = apply_jet_colormap(heatmap_matrix)
        heatmap_pil = Image.fromarray(heatmap_rgb, mode='RGB').resize((w, h), resample=Image.BILINEAR)

        # Blend original image (60%) and heatmap (40%)
        blended_pil = Image.blend(orig_pil, heatmap_pil, alpha=0.45)

        filename = f"heatmap_{uuid.uuid4().hex[:8]}.png"
        save_path = os.path.join(self.heatmap_dir, filename)
        blended_pil.save(save_path)

        return f"/heatmaps/{filename}"
