from microservices.service_factory import create_microservice_app
from microservices.models.report_generation import run as build_report

app = create_microservice_app("Report Generation Service", build_report)
