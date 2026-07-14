# Aliyun ECS Linux Runtime Contract

**Target:** Alibaba Cloud ECS x86_64, Ubuntu 24.04 LTS
**Deployment:** Docker Compose single-host
**Purpose:** Course/competition/internal demo — NOT public production

## Minimum instance spec

| Resource | Recommended |
|----------|-------------|
| vCPU | 4 |
| RAM | 16 GiB |
| Disk | 100 GiB persistent |
| OS | Ubuntu 24.04 LTS (official Alibaba Cloud image) |

## Services

| Service | Port | Notes |
|---------|------|-------|
| Caddy | 443 (TLS) | Reverse proxy, terminates HTTPS/WSS |
| API | 8000 (internal) | FastAPI single worker, A package in-process |
| MySQL | 3306 (internal) | No public binding |
| Redis | 6379 (internal) | No public binding |
| Migrate | - | Runs once, then exits |

## Security

- TLS via Caddy (self-signed for demo, real certs for production)
- Secrets via Docker secrets (external files, never in env/image)
- MySQL/Redis: no host port binding
- Non-root API container
- All secrets external to repository

## Not in scope

- ECS purchase, console configuration, or deployment tutorials
- Embedded deployment, ARM, cross-compilation
- CARLA (explicitly excluded, verified zero-dependency)
- Multi-tenant, Kubernetes, or cloud-native orchestration

## Recovery targets (demo)

| Metric | Target |
|--------|--------|
| RPO | 24 hours |
| RTO | 4 hours |
| Backup rotation | 7 days |
| Deletion tombstone | 30 days |
