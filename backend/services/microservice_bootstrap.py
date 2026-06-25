import asyncio
import os
import subprocess
import sys

import httpx
from loguru import logger

from services.pipeline_logger import log_pipeline_event, log_pipeline_error
from services.service_registry import get_microservices


def should_autostart_microservices() -> bool:
    value = os.getenv("MARITIME_AUTOSTART_MICROSERVICES", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _creationflags() -> int:
    if os.name == "nt":
        return subprocess.CREATE_NO_WINDOW
    return 0


async def _service_is_ready(spec, timeout_seconds: float = 1.0) -> bool:
    try:
        async with httpx.AsyncClient(base_url=spec.url, timeout=timeout_seconds) as client:
            response = await client.get("/health")
            return response.status_code == 200
    except Exception:
        return False


def _launch_process(spec) -> subprocess.Popen:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        spec.entrypoint,
        "--host",
        "127.0.0.1",
        "--port",
        str(spec.port),
        "--reload",
    ]
    logger.info(f"Launching {spec.title} on {spec.url} (port {spec.port})")
    log_pipeline_event(
        None,
        spec.key,
        "service_launch",
        "launching local microservice process",
        url=spec.url,
        port=spec.port,
        entrypoint=spec.entrypoint,
    )
    return subprocess.Popen(
        command,
        cwd=os.path.dirname(os.path.dirname(__file__)),
        creationflags=_creationflags(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def ensure_microservices_running():
    launched_processes = []
    launched_specs = []
    microservices = get_microservices()
    for spec in microservices:
        if await _service_is_ready(spec):
            logger.info(f"{spec.title} already healthy")
            log_pipeline_event(None, spec.key, "service_ready", "microservice already healthy", url=spec.url, port=spec.port)
            continue

        if not should_autostart_microservices() or not spec.is_local:
            logger.info(f"{spec.title} is configured remotely at {spec.url}")
            log_pipeline_event(None, spec.key, "service_remote", "microservice configured remotely", url=spec.url, port=spec.port)
            continue

        launched_processes.append(_launch_process(spec))
        launched_specs.append(spec)

    for spec in launched_specs:
        for _ in range(60):
            if await _service_is_ready(spec):
                logger.info(f"{spec.title} ready")
                log_pipeline_event(None, spec.key, "service_ready", "local microservice became healthy", url=spec.url, port=spec.port)
                break
            await asyncio.sleep(0.5)
        else:
            log_pipeline_error(None, spec.key, "local microservice failed to start", url=spec.url, port=spec.port)
            raise RuntimeError(f"{spec.title} failed to start on {spec.url}")

    return launched_processes
