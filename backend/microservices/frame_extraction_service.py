from microservices.service_factory import create_microservice_app
from microservices.models.frame_extraction import run as build_frame_extraction

app = create_microservice_app("Frame Extraction Service", build_frame_extraction)
