PIPELINE_STAGES = [
    {
        "name": "combined_ai",
        "status_running": "COMBINED_AI_RUNNING",
        "status_completed": "COMBINED_AI_COMPLETED",
        "endpoint_env": "COMBINED_AI_URL",
        "progress_start": 10,
        "progress_end": 50,
        "stage_name": "Combined AI Processing",
        "requires_video": True,
        "is_local": False
    },
    {
        "name": "temporal_consistency",
        "status_running": "TEMPORAL_RUNNING",
        "status_completed": "TEMPORAL_COMPLETED",
        "endpoint_env": "TEMPORAL_URL",
        "progress_start": 50,
        "progress_end": 60,
        "stage_name": "Temporal Consistency",
        "requires_video": False,
        "is_local": True
    },
    {
        "name": "unique_defect",
        "status_running": "UNIQUE_DEFECT_RUNNING",
        "status_completed": "UNIQUE_DEFECT_COMPLETED",
        "endpoint_env": "UNIQUE_DEFECT_URL",
        "progress_start": 60,
        "progress_end": 70,
        "stage_name": "Unique Defect Extraction",
        "requires_video": False,
        "is_local": True
    },
    {
        "name": "area_estimation",
        "status_running": "AREA_RUNNING",
        "status_completed": "AREA_COMPLETED",
        "endpoint_env": "AREA_URL",
        "progress_start": 70,
        "progress_end": 80,
        "stage_name": "Area & Severity Estimation",
        "requires_video": False,
        "is_local": False
    },
    {
        "name": "cost_estimation",
        "status_running": "COST_ESTIMATION_RUNNING",
        "status_completed": "COST_ESTIMATION_COMPLETED",
        "endpoint_env": "COST_URL",
        "progress_start": 80,
        "progress_end": 90,
        "stage_name": "Cost Estimation",
        "requires_video": False,
        "is_local": True
    },
    {
        "name": "report_generation",
        "status_running": "REPORT_RUNNING",
        "status_completed": "REPORT_COMPLETED",
        "endpoint_env": "REPORT_URL",
        "progress_start": 90,
        "progress_end": 100,
        "stage_name": "Report Generation",
        "requires_video": False,
        "is_local": True
    }
]
