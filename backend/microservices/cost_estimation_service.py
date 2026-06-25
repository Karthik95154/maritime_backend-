from microservices.service_factory import create_microservice_app
from microservices.models.cost_estimation import run as build_cost_estimation

app = create_microservice_app("Cost Estimation Service", build_cost_estimation)
