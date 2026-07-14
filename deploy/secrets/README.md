# Secrets Directory

This directory contains ONLY documentation. Actual secret files live outside the repository.

## Required secrets

| Secret | Purpose | Generation |
|--------|---------|------------|
| `encryption_key` | AES-256-GCM key (32 bytes hex) | `openssl rand -hex 32` |
| `jwt_secret` | JWT HS256 signing key (32+ chars) | `openssl rand -hex 32` |
| `refresh_secret` | Refresh token HMAC key (32+ chars) | `openssl rand -hex 32` |
| `crisis_signing_key` | Ed25519 private key for offline bundle | `openssl genpkey -algorithm ed25519` |

## DO NOT

- Commit secret files to Git
- Use default/example passwords in production
- Store secrets in environment variables
- Include secrets in Docker images
