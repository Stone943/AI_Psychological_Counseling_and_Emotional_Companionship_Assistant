# Secrets Directory

This directory contains ONLY documentation. Actual secret files live outside the repository.

## Required secrets

| Secret | Purpose | Generation |
|--------|---------|------------|
| `encryption_key` | AES-256-GCM key (32 bytes hex) | `openssl rand -hex 32` |
| `jwt_secret` | JWT HS256 signing key (32+ chars) | `openssl rand -hex 32` |
| `refresh_secret` | Refresh token HMAC key (32+ chars) | `openssl rand -hex 32` |
| `database_url` | Complete `mysql+asyncmy://...` URL used only as a Docker secret | Provision from the database account vault |
| `mysql_root_password` | MySQL bootstrap root password | `openssl rand -hex 32` |
| `mysql_password` | MySQL application account password (must match `database_url`) | `openssl rand -hex 32` |
| `crisis_signing_key` | Ed25519 private key for offline bundle | `openssl genpkey -algorithm ed25519` |

`deploy/compose.demo.yml` requires absolute host paths to the first six files.
It also requires reviewed SHA-256 image digests and `DEMO_DOMAIN`; see
`deploy/env.demo.example`. The encryption key file contains exactly 32 raw bytes
or their 64-character hexadecimal encoding.

## DO NOT

- Commit secret files to Git
- Use default/example passwords in production
- Store secrets in environment variables
- Include secrets in Docker images
