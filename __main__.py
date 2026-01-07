"""
Pulumi deployment for snowflake-emulator to Kubernetes.

This module deploys the snowflake-emulator (https://github.com/nnnkkk7/snowflake-emulator)
to a local Kubernetes cluster using Pulumi.

The snowflake-emulator is a lightweight Snowflake emulator built with Go and DuckDB
for local development and testing.
"""

import pulumi
import pulumi_kubernetes as k8s

# Get the current stack configuration
config = pulumi.Config()

# Image configuration - defaults to locally built image from https://github.com/nnnkkk7/snowflake-emulator
# IMPORTANT: This deployment uses the official nnnkkk7/snowflake-emulator repository
# Build the image locally: git clone https://github.com/nnnkkk7/snowflake-emulator.git && docker build -t snowflake-emulator:local .
# To use a different image, set image_name config: pulumi config set image_name <your-image-name>
image_name = config.get("image_name") or "snowflake-emulator:local"
image_pull_policy = config.get("image_pull_policy") or "Never"

# Define app labels
app_labels = {"app": "snowflake-emulator"}

# Create a namespace for the snowflake-emulator
namespace = k8s.core.v1.Namespace(
    "snowflake-emulator-ns",
    metadata={"name": "snowflake-emulator"},
)

# Deploy the snowflake-emulator
deployment = k8s.apps.v1.Deployment(
    "snowflake-emulator-deployment",
    metadata={
        "namespace": namespace.metadata["name"],
        "labels": app_labels,
    },
    spec={
        "replicas": 1,
        "selector": {"matchLabels": app_labels},
        "template": {
            "metadata": {"labels": app_labels},
            "spec": {
                "containers": [
                    {
                        "name": "snowflake-emulator",
                        "image": image_name,
                        "imagePullPolicy": image_pull_policy,
                        "ports": [
                            {
                                "containerPort": 8080,
                                "name": "http",
                            }
                        ],
                        "env": [
                            {
                                "name": "PORT",
                                "value": "8080",
                            },
                            {
                                "name": "DB_PATH",
                                "value": ":memory:",
                            },
                            {
                                "name": "STAGE_DIR",
                                "value": "/app/stages",
                            },
                        ],
                        "resources": {
                            "requests": {
                                "cpu": "100m",
                                "memory": "128Mi",
                            },
                            "limits": {
                                "cpu": "500m",
                                "memory": "512Mi",
                            },
                        },
                        "livenessProbe": {
                            "httpGet": {
                                "path": "/health",
                                "port": 8080,
                            },
                            "initialDelaySeconds": 30,
                            "periodSeconds": 10,
                        },
                        "readinessProbe": {
                            "httpGet": {
                                "path": "/health",
                                "port": 8080,
                            },
                            "initialDelaySeconds": 5,
                            "periodSeconds": 5,
                        },
                    }
                ],
            },
        },
    },
    opts=pulumi.ResourceOptions(depends_on=[namespace]),
)

# Create a ClusterIP service for internal access
service = k8s.core.v1.Service(
    "snowflake-emulator-service",
    metadata={
        "namespace": namespace.metadata["name"],
        "labels": app_labels,
    },
    spec={
        "type": "ClusterIP",
        "ports": [
            {
                "port": 8080,
                "targetPort": 8080,
                "protocol": "TCP",
                "name": "http",
            }
        ],
        "selector": app_labels,
    },
    opts=pulumi.ResourceOptions(depends_on=[deployment]),
)

# Create a LoadBalancer service for external access (NodePort on Kind)
load_balancer_service = k8s.core.v1.Service(
    "snowflake-emulator-lb",
    metadata={
        "namespace": namespace.metadata["name"],
        "labels": app_labels,
        "name": "snowflake-emulator-external",
    },
    spec={
        "type": "LoadBalancer",
        "ports": [
            {
                "port": 8081,
                "targetPort": 8080,
                "protocol": "TCP",
                "name": "http",
            }
        ],
        "selector": app_labels,
    },
    opts=pulumi.ResourceOptions(depends_on=[deployment]),
)

# Export stack outputs
pulumi.export("namespace", namespace.metadata["name"])
pulumi.export("deployment_name", deployment.metadata["name"])
pulumi.export("service_name", service.metadata["name"])
pulumi.export("service_port", service.spec["ports"][0]["port"])
pulumi.export("external_service_name", load_balancer_service.metadata["name"])
pulumi.export("external_port", load_balancer_service.spec["ports"][0]["port"])
pulumi.export("access_url", "http://localhost:8081")
pulumi.export("health_check_url", "http://localhost:8081/health")

