from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTasks
import os
import cv2
import uuid
import json
import zipfile
import shutil

app = FastAPI(title="Colab Frame Extraction Worker")

@app.post("/process/{inspection_id}")
async def process_video_endpoint(
    request: Request,
    inspection_id: str,
    video: UploadFile = File(...)
):
    import traceback
    try:
        form = await request.form()
        print("PATH INSPECTION_ID:", inspection_id)
        print("FORM KEYS:", list(form.keys()))
        
        for key in form.keys():
            print("FORM FIELD:", key)

        print("=== WORKER RECEIVED REQUEST ===")
        print(f"[{inspection_id}] Request received")
    
        video_path = os.path.abspath(f"{inspection_id}.mp4")
        frames_dir = os.path.abspath(f"frames_{inspection_id}")
        os.makedirs(frames_dir, exist_ok=True)
        
        print(f"[{inspection_id}] Video save start -> {video_path}")
        try:
            with open(video_path, "wb") as f:
                while chunk := await video.read(1024 * 1024):  # 1MB chunks
                    f.write(chunk)
            print(f"[{inspection_id}] Video save complete. Size: {os.path.getsize(video_path)} bytes")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to save uploaded video: {e}")

        print(f"[{inspection_id}] Frame extraction start")
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video")

        frames = []
    frame_id = 1
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        frame_name = f"frame_{frame_id:03d}.jpg"
        frame_path = os.path.join(frames_dir, frame_name)
        
        # Save physical image
        cv2.imwrite(frame_path, frame)
        
        frames.append({
            "inspection_id": inspection_id,
            "frame_id": str(frame_id),
            "timestamp": timestamp,
            "frame_path": frame_name
        })
        frame_id += 1
        
        if frame_id > 5:
            break
            
        cap.release()
        if os.path.exists(video_path):
            os.remove(video_path)
            
        print(f"[{inspection_id}] Frame extraction complete. Total frames: {len(frames)}")

        print(f"[{inspection_id}] Metadata generation")
        metadata = {
            "inspection_id": inspection_id,
            "total_frames": len(frames),
            "frames": frames
        }
    
        meta_path = os.path.abspath(f"metadata_{inspection_id}.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f)
            
        print(f"[{inspection_id}] Zip creation start")
        zip_filename = os.path.abspath(f"{inspection_id}_output.zip")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            zipf.write(meta_path, "metadata.json")
            for root, _, files in os.walk(frames_dir):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.join("frames", file))
        print(f"[{inspection_id}] Zip creation complete")

        from starlette.background import BackgroundTask

        def cleanup_files(z_path, m_path, f_dir):
            print(f"[{inspection_id}] Cleanup task triggered for {z_path}")
            if os.path.exists(z_path): os.remove(z_path)
            if os.path.exists(m_path): os.remove(m_path)
            if os.path.exists(f_dir): shutil.rmtree(f_dir)

        print(f"[{inspection_id}] ZIP EXISTS: {os.path.exists(zip_filename)}")
        print(f"[{inspection_id}] ZIP SIZE: {os.path.getsize(zip_filename)} bytes")
        print(f"[{inspection_id}] ZIP PATH: {zip_filename}")

        print(f"[{inspection_id}] FileResponse creation")
        return FileResponse(
            zip_filename,
            media_type="application/zip",
            filename=f"{inspection_id}.zip",
            background=BackgroundTask(cleanup_files, zip_filename, meta_path, frames_dir)
        )
    except Exception as e:
        print(f"[{inspection_id}] UNHANDLED EXCEPTION IN WORKER:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8101)
