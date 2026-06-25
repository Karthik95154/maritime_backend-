import time
import logging
from fastapi import FastAPI, Request

# Configure basic logging to ensure we see the output in Docker logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def create_microservice_app(title: str, infer_handler):
    app = FastAPI(title=title, version="1.0.0")

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        # Get the internal port that this container is running on
        server_port = request.scope.get("server", [None, "Unknown"])[1]
        
        logger.info(f"[{title}] 🟢 INCOMING: {request.method} {request.url.path} | Port Hit: {server_port}")
        
        response = await call_next(request)
        
        process_time = (time.time() - start_time) * 1000
        logger.info(f"[{title}] 🔴 OUTGOING: Status {response.status_code} | Time Taken: {process_time:.2f}ms")
        
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": title}

    @app.post("/infer")
    async def infer(payload: dict):
        return await infer_handler(payload)

    return app
