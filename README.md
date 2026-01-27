# Snowflake Emulator on Kubernetes with Pulumi

Deploy Snowflake Emulator to local Kubernetes cluster created with `kind` using pulumi.

The deployment uses the [snowflake-emulator](https://github.com/nnnkkk7/snowflake-emulator) - a lightweight Snowflake-compatible database built with Go and DuckDB.

## Architecture

- **Snowflake Emulator** - Snowflake-compatible database server (1 replica)
- **Kind Cluster** - Local Kubernetes cluster (1 control-plane + 7 workers)

## Prerequisites

### 1. Install Docker Desktop

Download and install from [docker.com](https://www.docker.com/products/docker-desktop/)

Configure Docker Resources to have 4 CPUs, 8GB of memory, 2GB of swap.

### 2. Install Homebrew (macOS)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### 3. Install Required Tools

```bash
brew install kind kubectl helm pulumi uv
```

### 4. Create the Kind Cluster

This project deploys to the shared `local` kind cluster. Make sure it's running:

```bash
kind get clusters
# Should show 'local' in the list

kubectl cluster-info --context kind-local
# Should show cluster info for the local cluster

kubectl get nodes --context kind-local
# Should show 8 nodes (1 control-plane + 7 workers)
```

If the cluster doesn't exist, create it using the configuration from the parent directory:

```bash
# From the pulumi-snowflake directory
kind create cluster --config kind-config.yaml
```

### 5. Configure Pulumi for Local State

```bash
pulumi login file://~
```

This stores Pulumi state locally instead of in Pulumi Cloud.

Set your Pulumi passphrase as an environment variable (add to your `~/.zshrc` or `~/.bashrc`):

```bash
export PULUMI_CONFIG_PASSPHRASE=""
```

This passphrase encrypts your Pulumi secrets. For local development, an empty passphrase is acceptable.

### 6. Build Snowflake Emulator Docker Image

Build the snowflake-emulator image from the official repository:

```bash
# Clone the official snowflake-emulator repository
git clone https://github.com/nnnkkk7/snowflake-emulator.git /tmp/snowflake-emulator
cd /tmp/snowflake-emulator

# Build the Docker image
docker build -t snowflake-emulator:local .

# Load the image into your Kind cluster
kind load docker-image snowflake-emulator:local --name local

# Navigate back to the pulumi-snowflake project
cd /Users/daniel.nuriyev/repos/pulumi-snowflake
```

### 7. Install Python Dependencies

```bash
uv sync
```

### 8. Initialize Pulumi Stack

If this is a fresh clone, initialize the dev stack:

```bash
pulumi stack init dev
```

## Deploy

```bash
pulumi up --yes --stack dev
```

Once deployment completes (typically 10-30 seconds), all services will be running and ready to use.

## Deployment Status

After a successful deployment, you should see the pod and services in the `Running` state:

```bash
kubectl get pods -n snowflake-emulator --context kind-local
kubectl get svc -n snowflake-emulator --context kind-local
```

Expected output:
```
NAME                                                      READY   STATUS    RESTARTS   AGE
snowflake-emulator-deployment-XXXXXXXX-XXXXXXXXXX        1/1     Running   0          Xs

NAME                                  TYPE        CLUSTER-IP      PORT(S)          AGE
snowflake-emulator-external           NodePort    10.96.79.60     8081:30081/TCP   Xs
snowflake-emulator-service-XXXXXXXX   ClusterIP   10.96.184.233   8080/TCP         Xs
```

## Access Services

After deployment, the Snowflake Emulator is accessible via port-forward:

```bash
kubectl port-forward -n snowflake-emulator svc/snowflake-emulator-external 8081:8081 --context kind-local
```

Then access at `http://localhost:8081` in your browser or via API.

### Health Check

```bash
curl http://localhost:8081/health
```

Expected response: `OK` with HTTP 200 status

### REST API v2 Examples

```bash
# Execute SQL statement
curl -X POST http://localhost:8081/api/v2/statements \
  -H "Content-Type: application/json" \
  -d '{"statement": "SELECT 1"}'

# Create a database
curl -X POST http://localhost:8081/api/v2/databases \
  -H "Content-Type: application/json" \
  -d '{"name": "MY_DB"}'

# List warehouses
curl http://localhost:8081/api/v2/warehouses
```

## Cleanup

Destroy all resources:

```bash
pulumi destroy --yes --stack dev
```

**Note**: The local cluster is shared with other services and should not be deleted.

## Troubleshooting

### Check pod status

```bash
kubectl get pods -n snowflake-emulator --context kind-local
```

### View logs

```bash
kubectl logs -n snowflake-emulator deployment/snowflake-emulator-deployment-XXXXXXXX --context kind-local
```

### Restart a deployment

```bash
kubectl rollout restart deployment/snowflake-emulator-deployment-XXXXXXXX -n snowflake-emulator --context kind-local
```

### Pod not starting

If pods are crashing or stuck in `CrashLoopBackOff`:

1. Check available node resources:
   ```bash
   kubectl describe nodes --context kind-local
   ```

2. Check pod resource usage:
   ```bash
   kubectl top pods -n snowflake-emulator --context kind-local
   ```

3. Check logs for error messages:
   ```bash
   kubectl logs -n snowflake-emulator deployment/snowflake-emulator-deployment-XXXXXXXX --context kind-local
   ```

## Deployment Summary

This deployment creates a fully functional Snowflake Emulator environment on Kubernetes with:

✅ **Snowflake Emulator** - Snowflake-compatible database (1 replica)  
✅ **ClusterIP Service** - Internal access for other services  
✅ **NodePort Service** - External access via localhost:8081  
✅ **Health Checks** - Liveness and readiness probes configured  

### Default Configuration

- **Namespace**: `snowflake-emulator`
- **Replica Count**: 1
- **Container Port**: 8080 (internal)
- **NodePort**: 30081 (maps to localhost:8081 via kind-config.yaml)
- **Database**: In-memory `:memory:` (development)
- **CPU Request**: 100m, **Limit**: 500m
- **Memory Request**: 128Mi, **Limit**: 512Mi
- **Health Check**: `http://localhost:8081/health`

## Resources

- [Snowflake Emulator GitHub Repository](https://github.com/nnnkkk7/snowflake-emulator)
- [Pulumi Kubernetes Provider](https://www.pulumi.com/docs/reference/pkg/kubernetes/)
- [Pulumi Python SDK](https://www.pulumi.com/docs/reference/pkg/python/)
- [Kind Documentation](https://kind.sigs.k8s.io/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
