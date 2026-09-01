import os
import sys
import tarfile
import zipfile
import urllib.request
import numpy as np
import pandas as pd

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
MVTEC_DIR = os.path.join(DATA_DIR, "mvtec")
NASA_IMS_DIR = os.path.join(DATA_DIR, "nasa_ims")

def download_file(url: str, destination: str):
    """Downloads file with progress report"""
    print(f"Downloading {url} to {destination}...")
    def reporthook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size) if total_size > 0 else 0
        sys.stdout.write(f"\rDownloading: {percent}%")
        sys.stdout.flush()
    try:
        urllib.request.urlretrieve(url, destination, reporthook)
        print("\nDownload complete.")
        return True
    except Exception as e:
        print(f"\nDownload failed from {url}: {e}")
        return False

def generate_sample_mvtec_data(category: str = "bottle"):
    """Generates synthetic visual dataset matching MVTec AD folder layout if remote download is unavailable"""
    from PIL import Image, ImageDraw
    
    target_folder = os.path.join(MVTEC_DIR, category)
    train_good_dir = os.path.join(target_folder, "train", "good")
    test_good_dir = os.path.join(target_folder, "test", "good")
    test_defective_dir = os.path.join(target_folder, "test", "broken_large")
    
    os.makedirs(train_good_dir, exist_ok=True)
    os.makedirs(test_good_dir, exist_ok=True)
    os.makedirs(test_defective_dir, exist_ok=True)
    
    print(f"Generating synthetic MVTec AD '{category}' dataset images...")
    
    # Generate healthy training images
    for i in range(15):
        img = Image.new('RGB', (256, 256), color=(30, 30, 35))
        draw = ImageDraw.Draw(img)
        # Draw clean bottle outline
        draw.ellipse([80, 40, 176, 220], fill=(200, 210, 225), outline=(255, 255, 255))
        draw.rectangle([110, 20, 146, 50], fill=(180, 190, 205))
        img.save(os.path.join(train_good_dir, f"{i:03d}.png"))
        
    # Generate healthy test images
    for i in range(5):
        img = Image.new('RGB', (256, 256), color=(30, 30, 35))
        draw = ImageDraw.Draw(img)
        draw.ellipse([80, 40, 176, 220], fill=(200, 210, 225), outline=(255, 255, 255))
        draw.rectangle([110, 20, 146, 50], fill=(180, 190, 205))
        img.save(os.path.join(test_good_dir, f"{i:03d}.png"))

    # Generate defective test images (scratches / cracks)
    for i in range(5):
        img = Image.new('RGB', (256, 256), color=(30, 30, 35))
        draw = ImageDraw.Draw(img)
        draw.ellipse([80, 40, 176, 220], fill=(200, 210, 225), outline=(255, 255, 255))
        draw.rectangle([110, 20, 146, 50], fill=(180, 190, 205))
        # Draw sharp defect scratch
        draw.line([95 + i*5, 80, 150 - i*3, 160], fill=(220, 40, 40), width=4)
        draw.line([100, 120, 130, 140], fill=(255, 0, 0), width=3)
        img.save(os.path.join(test_defective_dir, f"{i:03d}.png"))

    print(f"Generated sample MVTec AD '{category}' visual dataset at {target_folder}.")

def setup_mvtec_dataset(category: str = "bottle"):
    """Downloads and extracts MVTec AD category (bottle or screw)"""
    os.makedirs(MVTEC_DIR, exist_ok=True)
    target_folder = os.path.join(MVTEC_DIR, category)
    
    if os.path.exists(target_folder) and os.listdir(target_folder):
        print(f"MVTec AD '{category}' category already exists at {target_folder}.")
        return

    # Public mirror URLs for MVTec AD categories
    urls = [
        f"https://dataset.djl.ai/resources/dataset/mvtec_ad/{category}.tar.xz",
        f"https://www.mvtec.com/fileadmin/Redaktion/mvtec.com/company/research/datasets/mvtec_ad/{category}.tar.xz"
    ]
    
    archive_path = os.path.join(MVTEC_DIR, f"{category}.tar.xz")
    success = False
    
    for url in urls:
        if download_file(url, archive_path):
            success = True
            break
            
    if success and os.path.exists(archive_path):
        print(f"Extracting {archive_path}...")
        try:
            with tarfile.open(archive_path, "r:xz") as tar:
                tar.extractall(path=target_folder)
            print(f"Extracted MVTec AD {category} dataset to {target_folder}.")
            return
        except Exception as e:
            print(f"Extraction error: {e}")

    # Fallback if download is unavailable
    generate_sample_mvtec_data(category)


def generate_sample_nasa_ims_data():
    """Generates synthetic run-to-failure vibration dataset matching NASA IMS bearing format"""
    os.makedirs(NASA_IMS_DIR, exist_ok=True)
    print("Generating synthetic NASA IMS bearing run-to-failure vibration telemetry...")
    
    np.random.seed(42)
    time_steps = 100  # 100 snapshot files representing bearing lifetime
    fs = 20480  # 20.48 kHz sampling frequency
    duration = 1.0  # 1 second snapshot
    num_samples = int(fs * duration)
    
    for step in range(time_steps):
        # Degradation factor increases exponentially as step approaches 100
        degradation = (step / time_steps) ** 3.5
        
        # Base healthy signal: 100Hz shaft frequency + random white noise
        t = np.linspace(0, duration, num_samples, endpoint=False)
        base_signal = 0.05 * np.sin(2 * np.pi * 100 * t) + 0.02 * np.random.randn(num_samples)
        
        # Bearing defect frequency (e.g. BPFI ~ 230Hz) spikes with degradation
        fault_signal = degradation * 0.8 * np.sin(2 * np.pi * 230 * t) * (1 + 0.5 * np.sin(2 * np.pi * 100 * t))
        # High frequency impact transients
        transient_noise = degradation * 0.3 * np.random.randn(num_samples)
        
        b1_ch1 = base_signal + fault_signal + transient_noise
        b1_ch2 = 0.8 * b1_ch1 + 0.01 * np.random.randn(num_samples)
        b2_ch1 = 0.05 * np.sin(2 * np.pi * 100 * t) + 0.02 * np.random.randn(num_samples) # Healthy reference bearing
        b2_ch2 = 0.05 * np.cos(2 * np.pi * 100 * t) + 0.02 * np.random.randn(num_samples)
        
        df = pd.DataFrame({
            "B1_Ch1": b1_ch1,
            "B1_Ch2": b1_ch2,
            "B2_Ch1": b2_ch1,
            "B2_Ch2": b2_ch2
        })
        
        filename = f"2004.02.12.00.{step:02d}.00"
        df.to_csv(os.path.join(NASA_IMS_DIR, filename), sep="\t", index=False, header=False)

    print(f"Generated 100 bearing vibration snapshot files in {NASA_IMS_DIR}.")

def setup_nasa_ims_dataset():
    """Downloads or generates NASA IMS Bearing Dataset"""
    os.makedirs(NASA_IMS_DIR, exist_ok=True)
    existing_files = [f for f in os.listdir(NASA_IMS_DIR) if not f.startswith(".")]
    
    if len(existing_files) >= 50:
        print(f"NASA IMS dataset files already present ({len(existing_files)} files).")
        return
        
    print("Setting up NASA IMS Bearing Dataset...")
    generate_sample_nasa_ims_data()

if __name__ == "__main__":
    print("=== TACET DISCORD Dataset Downloader ===")
    setup_mvtec_dataset("bottle")
    setup_nasa_ims_dataset()
    print("=== Dataset Setup Complete ===")
