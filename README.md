# Snowflake Emulator Deployment with Pulumi

This project deploys the [snowflake-emulator](https://github.com/nnnkkk7/snowflake-emulator) (a lightweight Snowflake emulator built with Go and DuckDB) to a local Kubernetes cluster using Pulumi and Python with `uv` for package management.

**Repository**: This deployment uses the official [nnnkkk7/snowflake-emulator](https://github.com/nnnkkk7/snowflake-emulator) repository. Make sure you build the Docker image from this repository before deploying.

## GitHub Repository Setup

This project is initialized as a git repository. To push to GitHub:

```bash
# Create a new repository on GitHub (via web interface or GitHub CLI)
# Then add the remote and push:
git remote add origin https://github.com/YOUR_USERNAME/pulumi-snowflake.git
git push -u origin main
```

Or using GitHub CLI:
```bash
gh repo create pulumi-snowflake --public --source=. --remote=origin --push
```

## Prerequisites

Before you begin, ensure you have the following installed:

1. **Local Kubernetes Cluster**: Set up using Kind with the provided configuration
   - See the root `k8s.md` for setup instructions
   - Cluster name: `local`
   - 8 nodes (1 control-plane + 7 workers)

2. **Pulumi CLI**: https://www.pulumi.com/docs/get-started/install/
   ```bash
   # macOS with Homebrew
   brew install pulumi
   
   # Other platforms: https://www.pulumi.com/docs/get-started/install/
   ```

3. **Python**: Version 3.9 or later
   ```bash
   python3 --version
   ```

4. **uv**: Fast Python package installer (https://docs.astral.sh/uv/getting-started/installation/)
   ```bash
   # macOS with Homebrew
   brew install uv
   
   # Or with pip
   pip install uv
   ```

5. **kubectl**: Kubernetes command-line tool, configured to access your local cluster
   ```bash
   kubectl config use-context kind-local
   kubectl cluster-info
   ```

6. **Docker**: For image management (optional, if using pre-built images)

## Quick Start

### 1. Setup the Kubernetes Cluster

If you haven't already created the local Kind cluster:

```bash
# From the root directory
kind create cluster --name local --config kind-config.yaml

# Verify the cluster
kubectl cluster-info --context kind-local
kubectl get nodes
```

### 2. Initialize Pulumi Stack

```bash
# Navigate to the pulumi-snowflake directory
cd pulumi-snowflake

# Login to Pulumi with local backend
pulumi login --local

# Create a new stack
pulumi stack init dev

# Verify you're using the correct kubectl context
kubectl config use-context kind-local
```

### 3. Install Dependencies with uv

```bash
# Install dependencies using uv
uv sync

# Verify installation
uv run python -m pip list | grep pulumi
```

### 4. Prepare the Docker Image

Before deploying, you need to build and load the snowflake-emulator image from the [official repository](https://github.com/nnnkkk7/snowflake-emulator) into your Kind cluster.

**Important**: This deployment uses the snowflake-emulator from https://github.com/nnnkkk7/snowflake-emulator. Make sure you're building from the correct repository.

```bash
# Clone the snowflake-emulator repository
git clone https://github.com/nnnkkk7/snowflake-emulator.git
cd snowflake-emulator

# Build the Docker image
docker build -t snowflake-emulator:local .

# Load the image into your Kind cluster
kind load docker-image snowflake-emulator:local --name local

# Navigate back to pulumi-snowflake
cd ../pulumi-snowflake
```

**Note**: The default configuration expects a locally built image named `snowflake-emulator:local`. If you want to use a different image, you can configure it:

```bash
# Set a custom image name
pulumi config set image_name nnnkkk7/snowflake-emulator:latest
pulumi config set image_pull_policy IfNotPresent
```

### 5. Preview the Deployment

```bash
# Preview what will be created (using uv to run with project environment)
uv run pulumi preview
```

Expected output:
- Kubernetes Namespace: `snowflake-emulator`
- Deployment: 1 replica of snowflake-emulator (from https://github.com/nnnkkk7/snowflake-emulator)
- ClusterIP Service: Internal access on port 8080
- LoadBalancer Service: External access on port 8081

### 6. Deploy the Snowflake Emulator

```bash
# Deploy to Kubernetes (automatically confirms changes)
uv run pulumi up --yes
```

### 7. Verify the Deployment

```bash
# Check namespace
kubectl get namespace snowflake-emulator

# Check deployment
kubectl get deployment -n snowflake-emulator

# Check pods
kubectl get pods -n snowflake-emulator

# Check services
kubectl get services -n snowflake-emulator

# View deployment logs
kubectl logs -n snowflake-emulator deployment/snowflake-emulator-deployment

# Test health endpoint
curl http://localhost:8081/health
```

Expected response: `OK` with HTTP 200 status

### Verify the Correct Emulator is Running

To confirm you're running the correct snowflake-emulator from https://github.com/nnnkkk7/snowflake-emulator:

```bash
# Check the pod image
kubectl describe pod -n snowflake-emulator -l app=snowflake-emulator | grep Image

# Test REST API v2 endpoint (unique to nnnkkk7/snowflake-emulator)
curl -X POST http://localhost:8081/api/v2/statements \
  -H "Content-Type: application/json" \
  -d '{"statement": "SELECT 1"}'

# Check logs for emulator startup
kubectl logs -n snowflake-emulator deployment/snowflake-emulator-deployment | head -20
```

The logs should show the snowflake-emulator server starting up, and the REST API should respond with statement handles (UUIDs).

## Project Structure

```
pulumi-snowflake/
├── __main__.py          # Main Pulumi deployment code (Python)
├── Pulumi.yaml          # Pulumi project configuration
├── pyproject.toml       # Python project dependencies (uv)
├── .gitignore          # Git ignore patterns
└── README.md           # This file
```

## Configuration

### Kubernetes Resources Created

The deployment creates the following Kubernetes resources:

1. **Namespace**: `snowflake-emulator`
2. **Deployment**: Single replica with health checks
3. **Service (ClusterIP)**: Internal access via `snowflake-emulator-service:8080`
4. **Service (LoadBalancer)**: External access via `localhost:8081`

### Environment Variables

The snowflake-emulator container is configured with:

- `PORT`: 8080 (internal container port)
- `DB_PATH`: `:memory:` (in-memory DuckDB database for development)
- `STAGE_DIR`: `/app/stages` (directory for internal stage files)

### Resource Limits

Pod resource constraints:

- **CPU Request**: 100m, **Limit**: 500m
- **Memory Request**: 128Mi, **Limit**: 512Mi

### Health Checks

- **Liveness Probe**: HTTP GET `/health` every 10 seconds (after 30s initial delay)
- **Readiness Probe**: HTTP GET `/health` every 5 seconds (after 5s initial delay)

## Using the Snowflake Emulator

Once deployed and verified, you can interact with the emulator:

### REST API v2 Examples

```bash
# Health check
curl http://localhost:8081/health

# Execute SQL statement
curl -X POST http://localhost:8081/api/v2/statements \
  -H "Content-Type: application/json" \
  -d '{
    "statement": "SELECT IFF(1 > 0, '\''yes'\'', '\''no'\'')",
    "database": "TEST_DB",
    "schema": "PUBLIC"
  }'

# Create a database
curl -X POST http://localhost:8081/api/v2/databases \
  -H "Content-Type: application/json" \
  -d '{"name": "MY_DB"}'

# List warehouses
curl http://localhost:8081/api/v2/warehouses
```

### Go Snowflake Driver

Use the examples from the [snowflake-emulator repository](https://github.com/nnnkkk7/snowflake-emulator/tree/main/example/gosnowflake).

## Supported Features

The [snowflake-emulator](https://github.com/nnnkkk7/snowflake-emulator) supports:

- **SQL Operations**: SELECT, INSERT, UPDATE, DELETE, DDL (CREATE/DROP/ALTER)
- **Transactions**: BEGIN, COMMIT, ROLLBACK
- **Data Loading**: COPY INTO for CSV/JSON
- **Upsert Operations**: MERGE INTO
- **Snowflake Functions**: IFF, NVL, DATEADD, DATEDIFF, PARSE_JSON, etc.
- **Data Types**: Comprehensive Snowflake to DuckDB type mapping
- **REST API v2**: Full REST API v2 compatibility
- **Go Snowflake Driver**: Protocol-level gosnowflake compatibility

For full compatibility details, see the [snowflake-emulator documentation](https://github.com/nnnkkk7/snowflake-emulator).

## Building and Using Custom Images

The deployment is configured to use a locally built image by default. This ensures you're using the exact version from the [official repository](https://github.com/nnnkkk7/snowflake-emulator).

### Building from Source (Recommended)

```bash
# Clone the official repository
git clone https://github.com/nnnkkk7/snowflake-emulator.git
cd snowflake-emulator

# Build the Docker image
docker build -t snowflake-emulator:local .

# Load the image into your Kind cluster
kind load docker-image snowflake-emulator:local --name local

# The default configuration will use this image
cd ../pulumi-snowflake
uv run pulumi preview
```

### Using a Different Image

If you want to use a different image name or tag, configure it via Pulumi config:

```bash
# Set custom image name
pulumi config set image_name snowflake-emulator:custom
pulumi config set image_pull_policy IfNotPresent

# Or use a different tag
pulumi config set image_name snowflake-emulator:v0.0.7
```

**Note**: There is no official Docker Hub image for this project. You must build the image from the GitHub repository source.

## Troubleshooting

### Issue: Image Pull Errors

Since there's no official Docker Hub image, you must build the image locally:

```bash
# Build from the official repository
git clone https://github.com/nnnkkk7/snowflake-emulator.git
cd snowflake-emulator
docker build -t snowflake-emulator:local .

# Load into Kind cluster
kind load docker-image snowflake-emulator:local --name local

# Verify image is loaded
docker exec local-control-plane ctr images ls | grep snowflake-emulator
```

If you're using a custom image name, make sure it matches your Pulumi config:

```bash
# Check current image configuration
pulumi config get image_name

# Update if needed
pulumi config set image_name snowflake-emulator:local
pulumi config set image_pull_policy Never
```

### Issue: Pod Not Starting

```bash
# Check pod status
kubectl describe pod -n snowflake-emulator

# View pod logs
kubectl logs -n snowflake-emulator deployment/snowflake-emulator-deployment

# Check resource availability
kubectl top nodes
kubectl top pods -n snowflake-emulator
```

### Issue: Service Not Accessible

```bash
# Check service and endpoints
kubectl get svc -n snowflake-emulator
kubectl get endpoints -n snowflake-emulator

# Test connectivity within cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://snowflake-emulator-external:8081/health

# Test port forwarding
kubectl port-forward -n snowflake-emulator svc/snowflake-emulator-external 8081:8081
curl http://localhost:8081/health
```

### Issue: Port Already in Use

```bash
# Check what's using port 8081
lsof -i :8081

# Or find and kill the process
kill -9 $(lsof -t -i:8081)
```

## Monitoring and Logs

```bash
# View Pulumi stack outputs
pulumi stack output

# Stream deployment logs
kubectl logs -n snowflake-emulator deployment/snowflake-emulator-deployment -f

# Watch pod status
kubectl get pods -n snowflake-emulator --watch

# View namespace events
kubectl get events -n snowflake-emulator --sort-by='.lastTimestamp'

# Check Pulumi operation logs
pulumi logs
```

## Cleanup

### Remove the Deployment

```bash
# Destroy all resources created by Pulumi
pulumi destroy

# Confirm by typing 'yes' when prompted
```

### Remove the Stack

```bash
# Remove the stack configuration
pulumi stack rm dev
```

### Remove the Kubernetes Cluster (Optional)

```bash
# Delete the Kind cluster
kind delete cluster --name local
```

## Development

### Modifying the Deployment

To customize the deployment, edit `__main__.py`:

- Change resource limits and requests
- Modify replica count
- Update environment variables
- Adjust health check settings
- Add persistent volumes
- Configure different environments

### Testing Changes

```bash
# Preview changes without applying
pulumi preview

# Apply changes
pulumi up

# Verify the update
kubectl logs -n snowflake-emulator deployment/snowflake-emulator-deployment
curl http://localhost:8081/health
```

## Using with uv

The project uses `uv` for fast and reliable Python package management:

```bash
# Install dependencies
uv sync

# Run Python with the project environment
uv run python --version

# Run Pulumi commands (always use uv run to ensure correct environment)
uv run pulumi preview
uv run pulumi up
uv run pulumi destroy
```

**Important**: Always use `uv run` prefix when running Pulumi commands to ensure you're using the correct Python environment with all dependencies installed.

## Integration with Data Platform

This snowflake-emulator deployment is part of a larger data platform stack:

- **Minio** (Object Storage) - ports 9000/9001
- **Nessie** (Git-like Data Catalog) - port 19120
- **Trino** (Distributed SQL Query Engine) - port 8080
- **Snowflake Emulator** (this project) - port 8081
- **Dagster** (Data Orchestration) - ports 3000/4000/4266

## Contributing

1. Make changes to `__main__.py`
2. Test with `pulumi preview` and `pulumi up`
3. Update this README if needed
4. Verify with `pulumi stack output`

## Quick Reference

### Key Points

1. **Repository**: This deploys [nnnkkk7/snowflake-emulator](https://github.com/nnnkkk7/snowflake-emulator) - a lightweight Snowflake emulator built with Go and DuckDB
2. **Image**: Build locally from the GitHub repository (no Docker Hub image available)
3. **Python**: Uses `uv` for dependency management - always use `uv run` prefix
4. **Port**: Accessible at `http://localhost:8081` after deployment
5. **Health Check**: Available at `http://localhost:8081/health`

### Deployment Checklist

- [ ] Kind cluster `local` is running
- [ ] kubectl context is set to `kind-local`
- [ ] Docker image `snowflake-emulator:local` is built and loaded into Kind
- [ ] Dependencies installed with `uv sync`
- [ ] Pulumi stack `dev` is initialized
- [ ] Deployment verified with `kubectl get pods -n snowflake-emulator`
- [ ] Health check passes: `curl http://localhost:8081/health`

## Resources

- [Snowflake Emulator GitHub Repository](https://github.com/nnnkkk7/snowflake-emulator) - **Official repository used by this deployment**
- [Pulumi Kubernetes Provider](https://www.pulumi.com/docs/reference/pkg/kubernetes/)
- [Pulumi Python SDK](https://www.pulumi.com/docs/reference/pkg/python/)
- [Kind Documentation](https://kind.sigs.k8s.io/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
