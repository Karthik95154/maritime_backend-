from microservices.service_factory import create_microservice_app
from microservices.models.unique_defects import run as build_unique_defects

app = create_microservice_app("Unique Defect Service", build_unique_defects)
