import re
import os

with open("pipeline_runner.py", "r", encoding="utf-8") as f:
    content = f.read()

# Import GPU client
if "from services.gpu_client import GPUServiceClient" not in content:
    content = content.replace(
        "from session_manager import update_session",
        "from session_manager import update_session\nfrom services.gpu_client import GPUServiceClient"
    )

# Fix _paths to include gpu_json
if '"gpu_json":' not in content:
    content = content.replace(
        '"frame_json": os.path.join(session_folder, "module_1_frame_extraction_output", "extracted_frames.json"),',
        '"gpu_json": os.path.join(session_folder, "gpu_processing_output", "gpu_outputs.json"),\n        "frame_json": os.path.join(session_folder, "module_1_frame_extraction_output", "extracted_frames.json"),'
    )

new_gpu_stages = """
async def _run_gpu_processing(session_id, session_folder, video_path, trace):
    update_session(session_id, progress=10, status="processing", current_stage="Remote GPU Processing")
    paths = _paths(session_folder)
    
    gpu_url = os.getenv("GPU_SERVICE_URL", "https://postbox-onscreen-desecrate.ngrok-free.dev")
    gpu_client = GPUServiceClient(gpu_url)
    
    logger.info(f"[{session_id}] Checking health of Remote GPU Service...")
    is_healthy = await gpu_client.health_check()
    if not is_healthy:
        raise RuntimeError("GPU service unavailable. Please restart Colab GPU service.")
    
    log_pipeline_event(
        session_id,
        "gpu_processing",
        "stage_start",
        "starting remote gpu processing",
        video_path=video_path,
        output_target=paths["gpu_json"],
    )
    
    logger.info(f"[{session_id}] Fetching video {video_path} for GPU upload...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://127.0.0.1:8000{video_path}", timeout=30.0)
            resp.raise_for_status()
            video_data = resp.content
    except Exception as e:
        raise RuntimeError(f"Could not read local video file {video_path} for GPU processing: {e}")

    started_at = time.perf_counter()
    logger.info(f"[{session_id}] Dispatching video to GPU Colab Service. This may take a while...")
    update_session(session_id, progress=30, current_stage="GPU Processing (Extraction & AI)")
    
    try:
        gpu_result = await gpu_client.process_video(video_path, video_data)
    except Exception as e:
        raise RuntimeError(f"GPU processing failed: {e}")
        
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    
    frames = gpu_result.get("frames", [])
    logger.info(f"[{session_id}] GPU Processing Complete. Received {len(frames)} processed frames.")
    
    os.makedirs(os.path.dirname(paths["gpu_json"]), exist_ok=True)
    save_json(frames, paths["gpu_json"], session_id=session_id, stage_key="gpu_processing")
    
    trace.record(
        service="gpu-colab-service",
        event="output_persisted",
        status="ok",
        duration_ms=duration_ms,
        response={"frame_count": len(frames)},
        issues=[],
        note="remote GPU output written to disk",
    )
    log_pipeline_event(
        session_id,
        "gpu_processing",
        "stage_complete",
        "remote gpu processing completed",
        duration_ms=duration_ms,
        frame_count=len(frames),
        output_target=paths["gpu_json"],
    )
    
    return frames

async def _run_cpu_stages(session_id, session_folder, frames, trace):
    paths = _paths(session_folder)

    update_session(session_id, progress=65, current_stage="Temporal Consistency")
    temporal_spec = _service_spec("temporal_consistency")
    
    log_pipeline_event(
        session_id,
        "temporal_consistency",
        "stage_start",
        "starting temporal consistency stage",
        input_source="gpu_processing",
        output_target=paths["temporal_json"],
        frame_count=len(frames),
    )
    temporal_result, temporal_duration_ms, temporal_issues = await _call_microservice(
        session_id,
        trace,
        temporal_spec,
        {"session_id": session_id, "frames": frames},
    )
    save_json(temporal_result["tracks"], paths["temporal_json"], session_id=session_id, stage_key="temporal_consistency")
    
    unique_spec = _service_spec("unique_defects")
    log_pipeline_event(
        session_id,
        "unique_defects",
        "stage_start",
        "starting unique defect aggregation stage",
        input_source="temporal_consistency",
        output_target=paths["unique_json"],
        track_count=len(temporal_result["tracks"]),
    )
    unique_result, unique_duration_ms, unique_issues = await _call_microservice(
        session_id,
        trace,
        unique_spec,
        {"session_id": session_id, "tracks": temporal_result["tracks"]},
    )
    save_json(unique_result["unique_defects"], paths["unique_json"], session_id=session_id, stage_key="unique_defects")
    
    unique_outputs = unique_result.get("unique_defects", {})
    logger.info(f"[{session_id}] Unique Defects Aggregation Complete: Filtered down to {len(unique_outputs)} unique real-world defects.")
    
    # Confidence Check
    reasons = []
    low_frames = [
        item
        for item in frames
        if (item.get("classification") or {}).get("confidence", 1.0) < LOW_CLASSIFICATION_CONFIDENCE
    ]
    if low_frames:
        reasons.append(f"Low confidence in detecting part classification (deck/hull) in {len(low_frames)} frames")

    low_defect_confidence = []
    for defect in unique_result["unique_defects"].values():
        confidences = defect.get("confidence_statistics") or {}
        best_conf = float(confidences.get("max_confidence") or 0)
        avg_conf = float(confidences.get("avg_confidence") or 0)
        if best_conf < LOW_DEFECT_CONFIDENCE or avg_conf < LOW_DEFECT_AVG_CONFIDENCE:
            low_defect_confidence.append(defect)

    if low_defect_confidence:
        reasons.append(f"Low confidence in detecting defects for {len(low_defect_confidence)} items")

    if reasons:
        trace.record(
            service="workflow-orchestrator-service",
            event="human_review_gate",
            status="warning",
            issues=reasons,
            note="workflow paused for human review",
        )
        _pause_for_confidence_review(session_id, " and ".join(reasons), resume_from="post_confidence_review")
        return {"needs_review": True, "unique_outputs": unique_outputs, "trace": trace}

    return {"needs_review": False, "unique_outputs": unique_outputs, "trace": trace}
"""

# Replace the old _frame_extraction and _run_detection_and_confidence_review
pattern = re.compile(r'async def _frame_extraction.*?(?=async def _run_final_stages)', re.DOTALL)
content = pattern.sub(new_gpu_stages + '\n\n', content)

# Now update run_pipeline
new_run_pipeline = """async def run_pipeline(session_id, video_path, session_folder):
    try:
        log_pipeline_event(
            session_id,
            "orchestrator",
            "pipeline_start",
            "pipeline started",
            video_path=video_path,
            session_folder=session_folder,
        )
        trace = PipelineTraceWriter(session_id, session_folder)
        frames = await _run_gpu_processing(session_id, session_folder, video_path, trace)
        review_result = await _run_cpu_stages(session_id, session_folder, frames, trace)
        if not review_result["needs_review"]:
            await _run_final_stages(session_id, session_folder, trace, review_result["unique_outputs"])
            update_session(session_id, progress=100, status="completed", current_stage="Completed")
        log_pipeline_event(session_id, "orchestrator", "pipeline_complete", "pipeline completed successfully")
    except Exception as exc:
        logger.error(f"[{session_id}] Pipeline Failed")
        logger.error(str(exc))
        logger.error(traceback.format_exc())
        log_pipeline_error(session_id, "orchestrator", "pipeline failed", error=str(exc))
        update_session(session_id, status="failed", current_stage="Failed")


async def run_batch_pipeline(session_id, video_paths, session_folder, previous_frame_jsons):
    try:
        log_pipeline_event(
            session_id,
            "orchestrator",
            "pipeline_start",
            "batch pipeline started",
            video_count=len(video_paths),
            session_folder=session_folder,
        )
        trace = PipelineTraceWriter(session_id, session_folder)
        # For batch, we'll just process the first video with the GPU service for simplicity in this refactor
        # Or loop them. Let's loop them.
        all_frames = []
        for vp in video_paths:
            f = await _run_gpu_processing(session_id, session_folder, vp, trace)
            all_frames.extend(f)
            
        review_result = await _run_cpu_stages(session_id, session_folder, all_frames, trace)
        if not review_result["needs_review"]:
            await _run_final_stages(session_id, session_folder, trace, review_result["unique_outputs"])
            update_session(session_id, progress=100, status="completed", current_stage="Completed")
        log_pipeline_event(session_id, "orchestrator", "pipeline_complete", "batch pipeline completed successfully")
    except Exception as exc:
        logger.error(f"[{session_id}] Batch Pipeline Failed")
        logger.error(str(exc))
        logger.error(traceback.format_exc())
        log_pipeline_error(session_id, "orchestrator", "batch pipeline failed", error=str(exc))
        update_session(session_id, status="failed", current_stage="Failed")"""

pattern2 = re.compile(r'async def run_pipeline.*?async def resume_pipeline', re.DOTALL)
content = pattern2.sub(new_run_pipeline + '\n\n\nasync def resume_pipeline', content)

with open("pipeline_runner.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Rewrite successful")
