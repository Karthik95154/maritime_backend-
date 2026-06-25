from microservices.service_factory import create_microservice_app
from microservices.models.defect_detection import run as build_defect_detection

app = create_microservice_app("AI Defect Detection Service", build_defect_detection)
