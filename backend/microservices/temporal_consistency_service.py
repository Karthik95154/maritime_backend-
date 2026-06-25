from microservices.service_factory import create_microservice_app
from microservices.models.temporal_consistency import run as build_temporal_consistency

app = create_microservice_app("Temporal Consistency Service", build_temporal_consistency)
