import os
import json
import logging
import tempfile
import time
import shutil
from typing import Dict, Any

from database import db_instance
from routes.storage import _get_inspection_dir

logger = logging.getLogger(__name__)

# Import the local modules
from modules.temporal_consistency_module import TemporalConsistencyModule
from modules.unique_defect_frame_extraction_module import UniqueDefectFrameExtractor
from modules.repair_estimation_module import RepairEstimationModule
from modules.document_generation_module import DocumentGenerationModule
# from modules.defect_matching_engine import DefectMatchingEngine (Not found)

class StorageAdapter:
    """Helper to read/write artifacts using the central storage approach"""
    
    @staticmethod
    async def get_artifacts(inspection_id: str) -> dict:
        doc = await db_instance.db["inspection_artifacts"].find_one({"inspection_id": inspection_id})
        return doc or {}

    @staticmethod
    async def save_artifact(inspection_id: str, subfolder: str, filename: str, temp_file_path: str, artifact_category: str):
        """Moves a temporary file into the central storage and updates MongoDB"""
        target_dir = _get_inspection_dir(inspection_id, subfolder)
        target_path = os.path.join(target_dir, filename)
        
        # Move the file to central storage
        shutil.move(temp_file_path, target_path)
        
        normalized_path = target_path.replace("\\", "/")
        await db_instance.db["inspection_artifacts"].update_one(
            {"inspection_id": inspection_id},
            {"$push": {artifact_category: normalized_path}},
            upsert=True
        )
        logger.info(f"[{inspection_id}] Saved artifact {normalized_path} to {artifact_category}")
        return normalized_path

    @staticmethod
    def get_latest_json(artifacts: dict, keyword: str = "") -> str:
        reports = artifacts.get("reports", [])
        for r in reversed(reports):
            if r.endswith(".json") and keyword in r:
                return r
        for r in reversed(reports):
            if r.endswith(".json"):
                return r
        return None

class BaseLocalStageRunner:
    """Base class for all local modules to enforce a standard interface"""
    async def run(self, inspection_id: str) -> None:
        raise NotImplementedError()

class TemporalConsistencyRunner(BaseLocalStageRunner):
    async def run(self, inspection_id: str) -> None:
        artifacts = await StorageAdapter.get_artifacts(inspection_id)
        input_json = StorageAdapter.get_latest_json(artifacts)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "temporal_consistency_output.json")
            
            # Execute module
            module = TemporalConsistencyModule()
            if input_json and os.path.exists(input_json):
                module.process(input_json, out_path)
            else:
                logger.warning(f"[{inspection_id}] No tracking JSON found. Processing empty.")
                with open(out_path, "w") as f: json.dump([], f)
                
            # Save using storage adapter
            await StorageAdapter.save_artifact(
                inspection_id, "reports", "temporal_consistency_output.json", out_path, "reports"
            )

class UniqueDefectRunner(BaseLocalStageRunner):
    async def run(self, inspection_id: str) -> None:
        artifacts = await StorageAdapter.get_artifacts(inspection_id)
        input_json = StorageAdapter.get_latest_json(artifacts, "temporal_consistency_output")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "unique_defects_output.json")
            
            module = UniqueDefectFrameExtractor()
            if input_json and os.path.exists(input_json):
                module.process(input_json, out_path)
            else:
                logger.warning(f"[{inspection_id}] No input JSON found. Processing empty.")
                with open(out_path, "w") as f: json.dump([], f)
                
            await StorageAdapter.save_artifact(
                inspection_id, "reports", "unique_defects_output.json", out_path, "reports"
            )

class CostEstimationRunner(BaseLocalStageRunner):
    async def run(self, inspection_id: str) -> None:
        artifacts = await StorageAdapter.get_artifacts(inspection_id)
        # Try to get area estimation output first, fallback to unique defects
        input_json = StorageAdapter.get_latest_json(artifacts, "area_estimation")
        if not input_json or not os.path.exists(input_json):
            input_json = StorageAdapter.get_latest_json(artifacts, "unique_defects_output")
            
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "cost_estimation_output.json")
            
            module = RepairEstimationModule(knowledge_folder="repair_process_docs", currency="USD")
            if input_json and os.path.exists(input_json):
                module.process(input_json, out_path)
            else:
                logger.warning(f"[{inspection_id}] No input JSON found. Processing empty.")
                with open(out_path, "w") as f: json.dump({}, f)
                
            await StorageAdapter.save_artifact(
                inspection_id, "reports", "cost_estimation_output.json", out_path, "reports"
            )

class ReportGenerationRunner(BaseLocalStageRunner):
    async def run(self, inspection_id: str) -> None:
        artifacts = await StorageAdapter.get_artifacts(inspection_id)
        input_json = StorageAdapter.get_latest_json(artifacts, "cost_estimation_output")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            module = DocumentGenerationModule(gemini_model_name="gemini-2.5-flash", output_folder=tmpdir)
            if input_json and os.path.exists(input_json):
                doc_path = module.create_report(input_json)
            else:
                logger.warning(f"[{inspection_id}] No input JSON found. Processing empty.")
                # Fallback empty logic if needed
                empty_in = os.path.join(tmpdir, "empty.json")
                with open(empty_in, "w") as f: json.dump({}, f)
                doc_path = module.create_report(empty_in)
                
            if doc_path and os.path.exists(doc_path):
                filename = os.path.basename(doc_path)
                await StorageAdapter.save_artifact(
                    inspection_id, "reports", filename, doc_path, "reports"
                )

class LocalWorkerService:
    def __init__(self):
        self.runners: Dict[str, BaseLocalStageRunner] = {
            "temporal_consistency": TemporalConsistencyRunner(),
            "unique_defect": UniqueDefectRunner(),
            "cost_estimation": CostEstimationRunner(),
            "report_generation": ReportGenerationRunner()
        }

    async def execute_local_stage(self, stage_name: str, inspection_id: str, vessel_id: str, visit_id: str) -> dict:
        logger.info(f"[{inspection_id}] Stage '{stage_name}' execution STARTED (Local CPU)")
        start_time = time.time()
        
        if stage_name not in self.runners:
            logger.error(f"[{inspection_id}] Stage '{stage_name}' has no registered local runner")
            raise ValueError(f"Unknown local stage: {stage_name}")
            
        try:
            msg = (
                "START\n"
                "↓\n"
                "Read Mongo\n"
                "↓\n"
                "Read Storage\n"
                "↓\n"
                "Processing\n"
                "↓"
            )
            logger.info(f"\n{msg}")
            
            runner = self.runners[stage_name]
            # Standardized execution interface
            await runner.run(inspection_id)
            
            msg = (
                "Writing Outputs\n"
                "↓\n"
                "Mongo Updated\n"
                "↓\n"
                "SUCCESS"
            )
            logger.info(f"\n{msg}")
            
            execution_time = time.time() - start_time
            logger.info(f"[{inspection_id}] Stage '{stage_name}' execution COMPLETED in {execution_time:.2f}s")
            
            return {"status": "success", "stage": stage_name, "execution_time": execution_time}
            
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            logger.error(f"[{inspection_id}] Stage '{stage_name}' execution FAILED:\n{tb_str}")
            raise

local_worker = LocalWorkerService()
