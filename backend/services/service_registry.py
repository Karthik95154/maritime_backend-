import json
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from config import settings


@dataclass(frozen=True)
class MicroserviceSpec:
    key: str
    title: str
    entrypoint: str
    port: int
    stage_name: str
    service_url: str | None = None

    @property
    def url(self) -> str:
        if self.service_url:
            return self.service_url
        return f"http://127.0.0.1:{self.port}"

    @property
    def hostname(self) -> str:
        parsed = urlparse(self.url)
        return parsed.hostname or "127.0.0.1"

    @property
    def is_local(self) -> bool:
        return self.hostname in {"127.0.0.1", "localhost", "::1"}


DEFAULT_MICROSERVICES = [
    MicroserviceSpec("frame_extraction", "Frame Extraction Service", "microservices.frame_extraction_service:app", 8101, "Frame Extraction"),
    MicroserviceSpec("classification", "AI Classification Service", "microservices.classification_service:app", 8102, "AI Classification"),
    MicroserviceSpec("defect_detection", "AI Defect Detection Service", "microservices.defect_detection_service:app", 8103, "Defect Detection"),
    MicroserviceSpec("temporal_consistency", "Temporal Consistency Service", "microservices.temporal_consistency_service:app", 8104, "Temporal Consistency"),
    MicroserviceSpec("unique_defects", "Unique Defect Service", "microservices.unique_defect_service:app", 8105, "Unique Defect Extraction"),
    MicroserviceSpec("cost_estimation", "Cost Estimation Service", "microservices.cost_estimation_service:app", 8106, "Cost Estimation"),
    MicroserviceSpec("explainability", "Explainability Service", "microservices.explainability_service:app", 8107, "Explainability"),
    MicroserviceSpec("report_generation", "Report Generation Service", "microservices.report_generation_service:app", 8108, "Document Generation"),
    MicroserviceSpec("analytics", "Analytics Service", "microservices.analytics_service:app", 8109, "Analytics"),
]


def _env_var_name_for_service(key: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", key).strip("_").upper()
    return f"MICROSERVICE_{normalized}_URL"


def _service_url_from_env(key: str) -> str | None:
    value = os.getenv(_env_var_name_for_service(key), "").strip()
    return value or None


def _normalize_entry(entry: dict[str, Any]) -> MicroserviceSpec:
    key = str(entry["key"])
    service_url = _service_url_from_env(key) or entry.get("url") or entry.get("service_url")
    if entry.get("port") is not None:
        port = int(entry["port"])
    elif service_url:
        port = int(urlparse(service_url).port or 0)
    else:
        port = 0
    return MicroserviceSpec(
        key=key,
        title=str(entry.get("title") or entry["key"]),
        entrypoint=str(entry["entrypoint"]),
        port=port,
        stage_name=str(entry.get("stage_name") or entry["key"]),
        service_url=service_url,
    )


def get_microservices() -> list[MicroserviceSpec]:
    config_path = getattr(settings, "microservices_config_path", "").strip()
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                parsed = json.load(file)
            if isinstance(parsed, list):
                services = [_normalize_entry(item) for item in parsed if isinstance(item, dict)]
                if services:
                    return services
        except Exception:
            pass

    raw = getattr(settings, "microservices_json", "").strip()
    if not raw:
        return DEFAULT_MICROSERVICES

    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            return DEFAULT_MICROSERVICES
        services = [_normalize_entry(item) for item in parsed if isinstance(item, dict)]
        return services or DEFAULT_MICROSERVICES
    except Exception:
        return DEFAULT_MICROSERVICES
