from microservices.service_factory import create_microservice_app
from microservices.models.classification import run as build_classification

app = create_microservice_app("AI Classification Service", build_classification)
