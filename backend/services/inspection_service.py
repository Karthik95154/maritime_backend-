from datetime import datetime
from fastapi import HTTPException
from models import InspectionSession
from services.session_views import build_dashboard, build_defects, build_summary

class InspectionService:
    @staticmethod
    async def _all_sessions(db) -> list[InspectionSession]:
        docs = await db.inspection_sessions.find().sort("created_at", -1).to_list(length=None)
        return [InspectionSession(**doc) for doc in docs]

    @staticmethod
    async def _session_or_404(session_id: str, db) -> InspectionSession:
        doc = await db.inspection_sessions.find_one({"session_id": session_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Session not found")
        return InspectionSession(**doc)

    @staticmethod
    async def get_dashboard(db):
        sessions = await InspectionService._all_sessions(db)
        return build_dashboard(sessions)

    @staticmethod
    async def list_inspections(db):
        sessions = await InspectionService._all_sessions(db)
        return [build_summary(session) for session in sessions]

    @staticmethod
    async def list_batches(db):
        visits = await db.drydock_visits.find().sort("start_date", -1).to_list(length=None)
        
        response = []
        for v in visits:
            vid = v.get("visit_id")
            ship_id = v.get("ship_id")
            vessel = await db.vessels.find_one({"imo": ship_id})
            vessel_name = vessel.get("vessel_name") if vessel else "Unknown Vessel"
            
            sessions = await db.analysis_sessions.find({"visit_id": vid}).to_list(length=None)
            videos = []
            for s in sessions:
                videos.extend(s.get("uploaded_videos", []))
                
            response.append({
                "batchId": vid,
                "createdAt": v.get("start_date").isoformat() if v.get("start_date") else None,
                "vesselName": vessel_name,
                "imoNumber": ship_id,
                "status": v.get("status"),
                "videos": videos,
                "videoCount": len(videos)
            })
        return response

    @staticmethod
    async def latest_inspection(db):
        sessions = await InspectionService._all_sessions(db)
        if not sessions:
            raise HTTPException(status_code=404, detail="No inspection sessions found")
        return build_summary(sessions[0])

    @staticmethod
    async def inspection_progress(session_id: str, db):
        session = await InspectionService._session_or_404(session_id, db)
        summary = build_summary(session)
        stage_order = [
            "Frame Extraction",
            "Awaiting Frame Review",
            "CDS Detection",
            "Temporal Consistency",
            "Unique Defect Extraction",
            "Awaiting Defect Review",
            "Repair Estimation",
            "Document Generation",
        ]
        current_stage = summary["currentStage"]
        current_index = stage_order.index(current_stage) if current_stage in stage_order else 0
        steps = []

        for index, label in enumerate(stage_order):
            status = "todo"
            if summary["status"].lower() == "completed":
                status = "done"
            elif summary["status"].lower() == "failed":
                if index < current_index:
                    status = "done"
                elif index == current_index:
                    status = "error"
            elif index < current_index:
                status = "done"
            elif index == current_index:
                status = "active"
            steps.append({"label": label, "status": status})

        base_time = session.created_at or datetime.utcnow()
        if summary["status"].lower() == "failed":
            current_message = "Pipeline execution failed due to an error."
        else:
            current_message = "Internal team is verifying AI output before the next step." if "Awaiting" in current_stage else "Pipeline stage running"

        logs = [
            {"time": base_time.replace(microsecond=0).strftime("%H:%M:%S"), "message": "Video accepted and processing started"},
            {"time": base_time.replace(microsecond=0).strftime("%H:%M:%S"), "message": current_message},
            {"time": base_time.replace(microsecond=0).strftime("%H:%M:%S"), "message": f"Current stage: {current_stage}"},
        ]
        
        if summary["status"].lower() == "failed" and getattr(session, 'error_message', None):
             logs.append({"time": datetime.utcnow().replace(microsecond=0).strftime("%H:%M:%S"), "message": f"Error: {session.error_message}"})

        return {**summary, "steps": steps, "logs": logs}

    @staticmethod
    async def inspection_defects(session_id: str, db):
        session = await InspectionService._session_or_404(session_id, db)
        return {**build_summary(session), "defects": build_defects(session)}

    @staticmethod
    async def inspection_visualization(session_id: str, db):
        session = await InspectionService._session_or_404(session_id, db)
        defects = build_defects(session)
        return {
            **build_summary(session),
            "defects": defects,
            "markers": [
                {
                    "defectId": defect["defectId"],
                    "x": defect["marker"]["x"],
                    "y": defect["marker"]["y"],
                    "severity": defect["severity"],
                }
                for defect in defects
            ],
            "selectedDefectId": defects[0]["defectId"] if defects else None,
        }

    @staticmethod
    async def inspection_report(session_id: str, db):
        session = await InspectionService._session_or_404(session_id, db)
        defects = build_defects(session)
        summary = build_summary(session)
        return {
            **summary,
            "sections": [
                "1 Executive Summary",
                "2 Inspection Details",
                "3 Defect Summary",
                "4 Defect Analysis",
                "5 Repair Estimation",
                "6 Recommendations",
                "7 Annexures",
            ],
            "executiveSummary": (
                f"{summary['vesselName']} inspection identified {len(defects)} defects "
                f"with estimated repair exposure of INR {summary['totalEstimatedCost']:,.0f}."
            ),
            "defects": defects,
            "downloadDocxUrl": f"/api/v1/download/{session.session_id}" if summary["documentReady"] else None,
            "downloadPdfUrl": f"/api/v1/download/{session_id}/pdf" if summary["documentReady"] else None,
        }

    @staticmethod
    async def inspection_progression(session_id: str, db):
        session = await InspectionService._session_or_404(session_id, db)
        defects = build_defects(session)
        if defects:
            defect = defects[0]
            area = defect["area"]
            timeline = [
                {"label": "05 May 2024", "area": round(area * 0.50, 2), "severity": "Medium", "image": defect["thumbnail"], "sessionId": session.session_id},
                {"label": "20 Aug 2024", "area": round(area * 0.72, 2), "severity": "Medium", "image": defect["thumbnail"], "sessionId": session.session_id},
                {"label": "12 Dec 2024", "area": round(area * 0.86, 2), "severity": "High" if defect["severity"] == "High" else "Medium", "image": defect["thumbnail"], "sessionId": session.session_id},
                {"label": (session.created_at or datetime.utcnow()).strftime("%d %b %Y"), "area": round(area, 2), "severity": defect["severity"], "image": defect["thumbnail"], "sessionId": session.session_id},
            ]
            first = timeline[0]["area"]
            last = timeline[-1]["area"]
            growth = round((((last - first) / first) * 100), 0) if first else 0
            defect_id = defect["defectId"]
        else:
            timeline = []
            growth = 0
            defect_id = "N/A"

        return {
            **build_summary(session),
            "defectId": defect_id,
            "location": "Port Side - Mid Section",
            "timeline": timeline,
            "areaGrowthPercent": growth,
            "severityChange": f"{timeline[0]['severity']} -> {timeline[-1]['severity']}" if timeline else "Stable",
            "recommendedAction": "Repair recommended within 30 days" if growth > 25 else "Continue monitoring",
        }

    @staticmethod
    async def delete_inspection(session_id: str, db):
        try:
            result = await db.inspection_sessions.delete_one({"session_id": session_id})
            if result.deleted_count == 0:
                raise HTTPException(status_code=404, detail="Session not found")
            return {"status": "success", "message": "Inspection deleted"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_inspection_status(inspection_id: str, db):
        job = await db.inspection_jobs.find_one({"inspection_id": inspection_id})
        if not job:
            raise HTTPException(status_code=404, detail="Inspection job not found")
            
        session = await db.inspection_sessions.find_one({"session_id": inspection_id})
        if session:
            job["current_stage"] = session.get("current_stage")
            job["progress"] = session.get("progress")
            
        job["_id"] = str(job["_id"])
        return job

    @staticmethod
    async def get_inspection_frames(inspection_id: str, db):
        frames = await db.frame_results.find({"inspection_id": inspection_id}).to_list(length=None)
        for f in frames:
            f["_id"] = str(f["_id"])
        return frames

    @staticmethod
    async def get_inspection_cds_results(inspection_id: str, db):
        results = await db.cds_results.find({"inspection_id": inspection_id}).to_list(length=None)
        for r in results:
            r["_id"] = str(r["_id"])
        return results

    @staticmethod
    async def get_inspection_report(inspection_id: str, db):
        report = await db.reports.find_one({"inspection_id": inspection_id})
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        report["_id"] = str(report["_id"])
        return report

    @staticmethod
    async def get_pipeline_metrics(db):
        frames_extracted = await db.frame_results.count_documents({})
        
        pipeline_cds = await db.cds_results.find({}).to_list(length=None)
        detections_found = sum(len(c.get("detections", [])) for c in pipeline_cds)
        
        unique_defects = await db.unique_defects.count_documents({})
        
        pipeline_repairs = await db.repair_estimations.find({}).to_list(length=None)
        estimated_repair_cost = sum(r.get("estimated_cost", 0) for r in pipeline_repairs)
        
        pipeline_reports = await db.reports.count_documents({})
        
        return {
            "frames_extracted": frames_extracted,
            "detections_found": detections_found,
            "unique_defects": unique_defects,
            "estimated_repair_cost": estimated_repair_cost,
            "reports_generated": pipeline_reports
        }
