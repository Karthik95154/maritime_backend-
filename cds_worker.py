import os
import shutil
import zipfile
import json
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI()

# Simulated models loaded at startup
CLASSIFICATION_MODEL = None
DETECTION_MODEL = None
SEGMENTATION_MODEL = None

@app.on_event("startup")
async def startup_event():
    global CLASSIFICATION_MODEL, DETECTION_MODEL, SEGMENTATION_MODEL
    print("Loading models from /content/drive/MyDrive/sample_files/final_models (simulated)")
    # Load actual weights here when running on Colab
    CLASSIFICATION_MODEL = "loaded"
    DETECTION_MODEL = "loaded"
    SEGMENTATION_MODEL = "loaded"
    print("Models loaded successfully.")

def cleanup_files(*file_paths):
    for path in file_paths:
        try:
            if os.path.exists(path):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        except Exception as e:
            print(f"Error cleaning up {path}: {e}")

@app.post("/cds")
async def process_cds(
    background_tasks: BackgroundTasks,
    inspection_id: str = Form(...),
    frames_zip: UploadFile = File(...)
):
    print(f"Received CDS request for {inspection_id}")
    
    # 1. Save uploaded zip
    work_dir = f"/tmp/cds_{inspection_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    zip_path = os.path.join(work_dir, "input_frames.zip")
    with open(zip_path, "wb") as f:
        f.write(await frames_zip.read())
        
    # 2. Extract frames
    frames_dir = os.path.join(work_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(frames_dir)
        
    # 3. Process frames (Simulation of real models)
    masks_dir = os.path.join(work_dir, "masks")
    os.makedirs(masks_dir, exist_ok=True)
    
    classification_results = []
    detection_results = []
    segmentation_results = []
    
    frame_files = [f for f in os.listdir(frames_dir) if f.endswith('.jpg') or f.endswith('.png')]
    
    for frame_file in frame_files:
        frame_id = os.path.splitext(frame_file)[0]
        
        # Simulated Classification
        classification_results.append({
            "frame_id": frame_id,
            "part_name": "hull",
            "confidence": 0.95
        })
        
        # Simulated Detection
        detection_results.append({
            "frame_id": frame_id,
            "defect_type": "corrosion",
            "confidence": 0.88,
            "bbox": [100, 100, 200, 200]
        })
        
        # Simulated Segmentation (Copying frame as mask for simulation)
        src_frame = os.path.join(frames_dir, frame_file)
        dst_mask = os.path.join(masks_dir, frame_file)
        shutil.copy(src_frame, dst_mask)
        
        segmentation_results.append({
            "frame_id": frame_id,
            "mask_file": frame_file
        })
        
    # 4. Save results JSON
    with open(os.path.join(work_dir, "classification_results.json"), "w") as f:
        json.dump(classification_results, f)
    with open(os.path.join(work_dir, "detection_results.json"), "w") as f:
        json.dump(detection_results, f)
    with open(os.path.join(work_dir, "segmentation_results.json"), "w") as f:
        json.dump(segmentation_results, f)
        
    # 5. Zip outputs
    output_zip = f"/tmp/{inspection_id}_cds_output.zip"
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(os.path.join(work_dir, "classification_results.json"), "classification_results.json")
        zipf.write(os.path.join(work_dir, "detection_results.json"), "detection_results.json")
        zipf.write(os.path.join(work_dir, "segmentation_results.json"), "segmentation_results.json")
        
        for root, dirs, files in os.walk(masks_dir):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_file = os.path.join("masks", file)
                zipf.write(abs_file, rel_file)
                
    background_tasks.add_task(cleanup_files, work_dir, output_zip)
    
    return FileResponse(
        output_zip,
        media_type="application/zip",
        filename=f"{inspection_id}_cds_output.zip"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8102)
