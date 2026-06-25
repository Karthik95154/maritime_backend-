import asyncio
import base64
import copy
import hashlib
import json
import os
import time
from collections import Counter
from typing import Any
import httpx
import tempfile
from docx import Document
from bson import ObjectId

PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2X9XkAAAAASUVORK5CYII="
)

PARTS = ["hull", "deck", "bow", "rudder", "propeller", "anchor", "keel"]
DEFECT_TYPES = ["corrosion", "crack", "hole", "paint_failure", "deformation", "fouling"]
SEVERITIES = ["Low", "Medium", "High"]

def stable_int(*parts: Any) -> int:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return int(digest[:12], 16)

def _safe_name(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_") or "item"

async def ensure_asset_file(filename: str, data: bytes = PLACEHOLDER_PNG) -> str:
    async with httpx.AsyncClient() as client:
        try:
            files = {"file": (filename, data, "application/octet-stream")}
            response = await client.post("http://127.0.0.1:8000/api/v1/internal/upload", files=files, timeout=5.0)
            response.raise_for_status()
            return response.json().get("url")
        except Exception:
            b64 = base64.b64encode(data).decode('utf-8')
            return f"data:application/octet-stream;base64,{b64}"

async def _download_file(url: str) -> bytes:
    if url.startswith("data:"):
        return base64.b64decode(url.split(",", 1)[1])
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://127.0.0.1:8000{url}", timeout=10.0)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        raise RuntimeError(f"Cannot download {url}. Make sure orchestrator is reachable. Error: {e}")

async def simulate_latency(seed: int, minimum_ms: int, maximum_ms: int) -> int:
    return minimum_ms

def _read_json(path: str) -> Any:
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

async def build_frame_extraction(payload: dict[str, Any]) -> dict[str, Any]:
    return {"error": "GPU models must run remotely. This endpoint is disabled locally.", "issues": []}

async def build_classification(payload: dict[str, Any]) -> dict[str, Any]:
    return {"error": "GPU models must run remotely. This endpoint is disabled locally.", "issues": []}

async def build_defect_detection(payload: dict[str, Any]) -> dict[str, Any]:
    return {"error": "GPU models must run remotely. This endpoint is disabled locally.", "issues": []}

import logging
logger = logging.getLogger(__name__)

from modules.temporal_consistency_module import TemporalConsistencyModule
from modules.unique_defect_frame_extraction_module import UniqueDefectFrameExtractor
from modules.repair_estimation_module import RepairEstimationModule
from modules.document_generation_module import DocumentGenerationModule
from modules.defect_matching_engine import DefectMatchingEngine

async def build_temporal_consistency(payload: dict[str, Any]) -> dict[str, Any]:
    print("[CPU] Temporal Consistency Started")
    start_time = time.time()
    frames = payload.get("frames", [])
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f_in, \
         tempfile.NamedTemporaryFile(mode="r", delete=False, suffix=".json") as f_out:
        in_path = f_in.name
        out_path = f_out.name
        json.dump(frames, f_in)
        
    try:
        module = TemporalConsistencyModule()
        module.process(in_path, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            temporal_results = json.load(f)
    finally:
        if os.path.exists(in_path): os.remove(in_path)
        if os.path.exists(out_path): os.remove(out_path)
        
    print(f"[CPU] Temporal Consistency Completed in {time.time() - start_time:.2f}s")
    return {"tracks": temporal_results, "issues": []}

async def build_unique_defects(payload: dict[str, Any]) -> dict[str, Any]:
    print("[CPU] Unique Defect Extraction Started")
    start_time = time.time()
    temporal_tracks = payload.get("tracks", [])
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f_in, \
         tempfile.NamedTemporaryFile(mode="r", delete=False, suffix=".json") as f_out:
        in_path = f_in.name
        out_path = f_out.name
        json.dump(temporal_tracks, f_in)
        
    try:
        module = UniqueDefectFrameExtractor()
        module.process(in_path, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            unique_results = json.load(f)
    finally:
        if os.path.exists(in_path): os.remove(in_path)
        if os.path.exists(out_path): os.remove(out_path)
        
    print(f"[CPU] Unique Defect Extraction Completed in {time.time() - start_time:.2f}s")
    return {"unique_defects": unique_results, "issues": []}

async def build_cost_estimation(payload: dict[str, Any]) -> dict[str, Any]:
    print("[CPU] Repair Estimation Started")
    start_time = time.time()
    unique_defects = payload.get("unique_defects", {})
    session_id = payload.get("session_id", "default_session")
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f_in, \
         tempfile.NamedTemporaryFile(mode="r", delete=False, suffix=".json") as f_out:
        in_path = f_in.name
        out_path = f_out.name
        json.dump(unique_defects, f_in)
        
    try:
        module = RepairEstimationModule(knowledge_folder="repair_process_docs", currency="USD")
        module.process(in_path, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            repair_results = json.load(f)
            
        try:
            matcher = DefectMatchingEngine()
            matcher.process_session(session_id, out_path)
        except Exception as e:
            print(f"DefectMatchingEngine error: {e}")
            
    finally:
        if os.path.exists(in_path): os.remove(in_path)
        if os.path.exists(out_path): os.remove(out_path)
        
    print(f"[CPU] Repair Estimation Completed in {time.time() - start_time:.2f}s")
    return {"repair_summary": repair_results.get("repair_summary", {}), "defect_repairs": repair_results.get("defect_repairs", {}), "issues": []}

async def build_explainability(payload: dict[str, Any]) -> dict[str, Any]:
    repair_payload = payload.get("repair_payload", {})
    return {"explainability": {"status": "Derived from repair estimation documentation rules."}, "issues": []}

async def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    print("[CPU] Report Generation Started")
    start_time = time.time()
    repair_payload = payload.get("repair_payload", {})
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f_in:
        in_path = f_in.name
        json.dump(repair_payload, f_in)
        
    try:
        out_dir = os.path.join("outputs", "reports")
        os.makedirs(out_dir, exist_ok=True)
        module = DocumentGenerationModule(gemini_model_name="gemini-2.5-flash", output_folder=out_dir)
        doc_path = module.create_report(in_path)
    finally:
        if os.path.exists(in_path): os.remove(in_path)
        
    print(f"[CPU] Report Generation Completed in {time.time() - start_time:.2f}s")
    return {"document_path": doc_path, "document_generated": True, "issues": []}

async def build_analytics(payload: dict[str, Any]) -> dict[str, Any]:
    repair_payload = payload.get("repair_payload", {})
    summary = repair_payload.get("repair_summary", {})
    return {"analytics_path": "analytics.json", "snapshot": {"total_cost": summary.get("total_estimated_cost", 0)}, "issues": []}
