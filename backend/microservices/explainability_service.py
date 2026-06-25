from microservices.service_factory import create_microservice_app
from microservices.models.explainability import run as build_explainability

app = create_microservice_app("Explainability Service", build_explainability)
