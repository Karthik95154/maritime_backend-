from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InspectionSession(BaseModel):
    session_id: str
    batch_id: Optional[str] = None
    video_name: Optional[str] = None
    vessel_name: Optional[str] = None
    imo_number: Optional[str] = None
    vessel_type: Optional[str] = None
    gross_tonnage: Optional[str] = None
    inspector_name: Optional[str] = None
    location: Optional[str] = None
    inspection_date: Optional[str] = None
    comments: Optional[str] = None
    video_path: Optional[str] = None
    output_path: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = 0
    current_stage: Optional[str] = None
    document_path: Optional[str] = None
    review_checkpoint: Optional[str] = None
    review_status: Optional[str] = None
    review_notes: Optional[str] = None
    error_message: Optional[str] = None
    failed_stage: Optional[str] = None
    last_successful_stage: Optional[str] = None
    error_type: Optional[str] = None
    traceback: Optional[str] = None
    review_updated_at: Optional[datetime] = None
    review_updated_by: Optional[str] = None
    pipeline_resume_from: Optional[str] = None
    vessel_id: Optional[str] = None
    visit_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class Vessel(BaseModel):
    vessel_id: str
    imo: str
    vessel_name: str
    vessel_type: Optional[str] = None
    gross_tonnage: Optional[str] = None
    owner: Optional[str] = None
    operator: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    latest_report_version: Optional[int] = 0
    health_score: Optional[int] = 100
    last_inspection_date: Optional[datetime] = None

class DryDockVisit(BaseModel):
    visit_id: str
    ship_id: str
    visit_number: int
    visit_type: str = "Dry Dock"
    dockyard: Optional[str] = None
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    status: str = "Active" # Active, Completed
    report_version: int = 0
    total_defects: int = 0
    total_cost: float = 0.0
    visit_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AnalysisSession(BaseModel):
    session_id: str
    vessel_id: str
    visit_id: Optional[str] = None
    uploaded_videos: list[str] = []
    analysis_results: Optional[str] = None
    generated_cost: Optional[float] = 0.0
    generated_report: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Completed"

class FrameResult(BaseModel):
    inspection_id: str
    frame_name: str
    frame_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CDSResult(BaseModel):
    inspection_id: str
    frame_name: str
    classification: dict = {}
    detections: list = []
    segmentations: list = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class InspectionJob(BaseModel):
    inspection_id: str
    status: str = "UPLOADED"
    frame_extraction: str = "pending"
    cds: str = "pending"
    unique_defects: str = "pending"
    cost_estimation: str = "pending"
    report_generation: str = "pending"
    error_message: Optional[str] = None
    failed_stage: Optional[str] = None
    last_successful_stage: Optional[str] = None
    error_type: Optional[str] = None
    traceback: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UniqueDefect(BaseModel):
    inspection_id: str
    defect_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Report(BaseModel):
    inspection_id: str
    report_metadata: dict = {}
    download_location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DefectImage(BaseModel):
    inspection_id: str
    defect_id: str
    file_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MaskImage(BaseModel):
    inspection_id: str
    mask_id: str
    file_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReportRecord(BaseModel):
    report_id: str
    inspection_id: str
    vessel_id: Optional[str] = None
    visit_id: Optional[str] = None
    file_path: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class DefectRegister(BaseModel):
    defect_id: str
    inspection_id: str
    vessel_id: Optional[str] = None
    visit_id: Optional[str] = None
    part_name: str
    defect_type: str
    severity: str
    crop_path: str
    status: str = "OPEN"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ClassificationResult(BaseModel):
    inspection_id: str
    vessel_id: Optional[str] = None
    visit_id: Optional[str] = None
    frame_id: str
    part_name: str
    confidence: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SegmentationResult(BaseModel):
    inspection_id: str
    vessel_id: Optional[str] = None
    visit_id: Optional[str] = None
    frame_id: str
    mask_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TemporalTrack(BaseModel):
    track_id: str
    inspection_id: str
    vessel_id: Optional[str] = None
    visit_id: Optional[str] = None
    part_name: str
    defect_type: str
    frame_ids: list[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RepairEstimation(BaseModel):
    estimation_id: str
    defect_id: str
    inspection_id: str
    vessel_id: Optional[str] = None
    visit_id: Optional[str] = None
    severity: str
    area: float
    estimated_cost: float
    currency: str = "USD"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PipelineTrace(BaseModel):
    inspection_id: str
    stage: str
    status: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    input_artifacts: list = []
    output_artifacts: list = []
    exception_type: Optional[str] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None
