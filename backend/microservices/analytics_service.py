from microservices.service_factory import create_microservice_app
from microservices.models.analytics import run as build_analytics

app = create_microservice_app("Analytics Service", build_analytics)
