import tkinter as tk
from tkinter import filedialog
import subprocess
import os
import glob
import time
from PIL import Image

def run_odm():
    
    root = tk.Tk()
    root.withdraw()

    image_folder = filedialog.askdirectory(title="選擇圖像資料夾")
    if not image_folder:
        print("未選擇資料夾")
        return

    if not os.path.exists(image_folder):
        print("資料夾不存在")
        return

    image_files = glob.glob(os.path.join(image_folder, "*.jpg")) + \
                  glob.glob(os.path.join(image_folder, "*.jpeg")) + \
                  glob.glob(os.path.join(image_folder, "*.png")) + \
                  glob.glob(os.path.join(image_folder, "*.tiff"))

    if not image_files:
        print("資料夾中沒有圖片")
        return

    dataset_name = f"dataset_{int(time.time())}"
    project_path = os.path.join(os.getcwd(), "odm_project")
    os.makedirs(project_path, exist_ok=True)

    docker_cmd = [
        "docker", "run", "-t", "--rm",
        "-v", f"{os.path.abspath(image_folder).replace('\\', '/')}:/datasets/{dataset_name}/images",
        "-v", f"{os.path.abspath(project_path).replace('\\', '/')}:/datasets",
        "opendronemap/odm",
        "--project-path", "/datasets",
        dataset_name,
        "--fast-orthophoto",
        "--orthophoto-resolution", "0.1",
        "--matcher-type", "flann",
        "--feature-quality", "high"
    ]

    print("執行建圖中...")
    process = subprocess.run(docker_cmd, capture_output=True, text=True)

    if process.returncode == 0:
        print("建圖成功")
        
        tif_path = os.path.join(project_path, dataset_name, "odm_orthophoto", "odm_orthophoto.tif")
        jpg_path = os.path.join(project_path, dataset_name, "odm_orthophoto", "odm_orthophoto.jpg")

        if os.path.exists(tif_path):
            try:
                with Image.open(tif_path) as img:
                    img.convert("RGB").save(jpg_path, "JPEG", quality=100)
                print(f"已轉檔：{jpg_path}")
            except Exception as e:
                print(f"TIFF 轉 JPG 失敗：{str(e)}")
        else:
            print("找不到 TIFF 檔案")
    else:
        print(" 建圖失敗")
        print(process.stderr)

if __name__ == '__main__':
    run_odm()
