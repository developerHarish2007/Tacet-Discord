import os
import numpy as np
from PIL import Image

try:
    import torch
    import torch.nn as nn
    import torchvision.models as models
    import torchvision.transforms as transforms
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

class ResNetEmbeddingExtractor:
    def __init__(self, device: str = 'cpu'):
        self.has_torch = HAS_TORCH
        if self.has_torch:
            self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
            # Load pretrained ResNet-18 and strip classification head (avgpool output = 512-dim)
            resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
            self.feature_extractor = nn.Sequential(*list(resnet.children())[:-1]).to(self.device)
            self.feature_extractor.eval()
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])

    def get_embedding(self, image_path: str) -> np.ndarray:
        """
        Extracts 512-dimensional L2-normalized image embedding vector.
        """
        if not os.path.exists(image_path):
            # Fallback zero vector if file missing
            return np.zeros(512, dtype=np.float32)

        try:
            img = Image.open(image_path).convert('RGB')
        except Exception as e:
            print(f"Error opening image {image_path}: {e}")
            return np.zeros(512, dtype=np.float32)

        if self.has_torch:
            tensor = self.transform(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                feat = self.feature_extractor(tensor).squeeze().cpu().numpy() # (512,)
            norm = np.linalg.norm(feat) + 1e-8
            return (feat / norm).astype(np.float32)

        # Fallback NumPy spatial color/texture embedding
        img_resized = img.resize((32, 32))
        arr = np.array(img_resized, dtype=np.float32).flatten() # (3072,)
        # Project 3072 features to 512 dimensions deterministically
        np.random.seed(42)
        proj_matrix = np.random.randn(3072, 512).astype(np.float32)
        emb = np.dot(arr, proj_matrix)
        norm = np.linalg.norm(emb) + 1e-8
        return (emb / norm).astype(np.float32)

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Computes cosine similarity between two normalized 1D vectors"""
    vec1 = np.asarray(vec1, dtype=np.float32)
    vec2 = np.asarray(vec2, dtype=np.float32)
    
    norm1 = np.linalg.norm(vec1) + 1e-8
    norm2 = np.linalg.norm(vec2) + 1e-8
    
    dot_product = float(np.dot(vec1, vec2))
    sim = dot_product / (norm1 * norm2)
    return float(np.clip(sim, 0.0, 1.0))
