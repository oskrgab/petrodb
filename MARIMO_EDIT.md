# Marimo Edit Server Setup

This document explains the Docker-based setup for running marimo edit server with basic authentication.

## Overview

This setup provides a containerized marimo edit environment that:
- Runs in headless mode (no browser auto-open)
- Uses token-based basic authentication for security
- Connects to an existing Docker network
- Mounts the project directory for live file editing
- Persists changes back to the host filesystem

## Architecture

```
Host Machine
├── Project Files (mounted to container)
├── .env (configuration)
└── Docker Container
    ├── Python 3.12 + uv package manager
    ├── Project dependencies from pyproject.toml
    ├── marimo edit server (port 8080)
    └── Isolated .venv (not shared with host)
```

## Files Created

### `Dockerfile`
Builds a Python 3.12-slim container with:
- `uv` package manager for fast dependency installation
- Project dependencies from `pyproject.toml` and `uv.lock`
- Runs `marimo edit --headless` with authentication

### `docker-compose.yml`
Orchestrates the container with:
- User ID/Group ID mapping for file permissions
- Volume mounts for project files
- Environment variables for configuration
- Connection to external Docker network
- Port 8080 exposed for web access

### `.dockerignore`
Excludes unnecessary files from Docker build context:
- `.venv` (virtual environment)
- `.git` (version control)
- `.cache` (cache directories)
- `__pycache__`, `*.pyc` (Python bytecode)

### `.env.example`
Template for required environment variables

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Marimo authentication password
MARIMO_TOKEN_PASSWORD=your_secure_password_here

# Docker network IP address
MARIMO_IP_ADDRESS=174.44.0.106

# User/Group IDs (run 'id -u' and 'id -g')
UID=1000
GID=1000
```

#### Finding Your UID and GID

```bash
# Show all user info
id

# Get UID only
id -u

# Get GID only
id -g

# Add to .env automatically
echo "UID=$(id -u)" >> .env
echo "GID=$(id -g)" >> .env
```

**Note:** UID and GID are constant for your user account and won't change on reboot.

## Usage

### Initial Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your values:
   ```bash
   nano .env  # or your preferred editor
   ```

3. Build and start the container:
   ```bash
   docker compose build
   docker compose up -d
   ```

### Accessing Marimo

Navigate to `http://174.44.0.106:8080` (or your configured IP) and enter your token password.

**Authentication Methods:**
- **Login page**: Enter password when prompted
- **Query parameter**: `http://174.44.0.106:8080?access_token=your_password`
- **Basic auth header**: `Authorization: Basic base64("username:password")`

### Managing the Service

```bash
# Start the service
docker compose up -d

# Stop the service
docker compose down

# View logs
docker compose logs -f

# Rebuild after changes
docker compose build --no-cache
docker compose up -d

# Restart the service
docker compose restart
```

## File Permissions & Persistence

### How It Works

The container runs as your host user (UID:GID) to ensure proper file permissions:

1. **Volume Mount**: `.:/app` mounts your project directory into the container
2. **User Mapping**: Container runs as your user, not root
3. **Isolated .venv**: Container has its own virtual environment at `/app/.venv`
4. **Direct Persistence**: All changes in marimo are immediately reflected in your local files

### Why This Matters

- **Correct Ownership**: Files created/edited in marimo have your user's ownership
- **No Permission Errors**: You can edit files both in marimo and on your host
- **Git Integration**: Changes appear in git status immediately
- **No Data Loss**: Container removal doesn't affect your files

## Troubleshooting

### Permission Denied Errors

**Symptom:** Can't create or save files in marimo

**Solution:** Ensure UID and GID in `.env` match your user:
```bash
id -u  # Should match UID in .env
id -g  # Should match GID in .env
```

### UV Cache Errors

**Symptom:** `failed to create directory /.cache/uv`

**Solution:** Already configured via `UV_CACHE_DIR=/app/.cache/uv` in docker-compose.yml

### Tool Cache/Config Permission Errors

**Symptoms:**
- `Failed to create directory "//.duckdb": Permission denied`
- `mkdir -p failed for path /.config/matplotlib: Permission denied`
- Any `Permission denied` error for directories in `/`

**Root Cause:** Tools try to create cache/config directories but don't have write permissions to system directories

**Solution:** Comprehensive environment variable configuration in docker-compose.yml:
- `HOME=/app` - Sets home directory
- `XDG_CONFIG_HOME=/app/.config` - Config files (DuckDB, matplotlib, etc.)
- `XDG_CACHE_HOME=/app/.cache` - Cache files (pip, uv, etc.)
- `XDG_DATA_HOME=/app/.local/share` - Application data
- `MPLCONFIGDIR=/app/.config/matplotlib` - Matplotlib config

These follow the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/), which most modern tools respect. This is a **comprehensive solution** that works for virtually all Python tools and libraries.

### Network Connection Issues

**Symptom:** Can't access marimo at the configured IP

**Solution:**
1. Verify the external network exists: `docker network ls`
2. Check the IP is available in the network's subnet
3. Ensure no other container is using the same IP

### Port Already in Use

**Symptom:** `port is already allocated`

**Solution:** Change the host port in docker-compose.yml:
```yaml
ports:
  - "8081:8080"  # Use different host port
```

## Best Practices

### Security

1. **Strong Password**: Use a strong `MARIMO_TOKEN_PASSWORD`
2. **Don't Commit `.env`**: Already in `.gitignore`, keep it that way
3. **Network Isolation**: Only expose to trusted networks
4. **Regular Updates**: Rebuild container periodically for security patches

### Development Workflow

1. **Edit in marimo**: Use the browser interface for interactive development
2. **Changes Sync Automatically**: Files update on host immediately
3. **Use Git Normally**: Commit, push, pull as usual
4. **Container is Disposable**: Safe to rebuild/recreate anytime

### Performance

1. **Keep .dockerignore Updated**: Exclude large directories from builds
2. **Use `--no-cache` Sparingly**: Only when troubleshooting
3. **Monitor Container Resources**: Use `docker stats` to check usage

## Technical Details

### Volume Strategy

```yaml
volumes:
  - .:/app              # Mount entire project
  - /app/.venv          # Anonymous volume for container's venv
```

The anonymous volume `/app/.venv` "shadows" the host's `.venv` directory, preventing permission conflicts while allowing the container to maintain its own isolated Python environment.

### Environment Variables

**Build-time (in Dockerfile):**
- `UV_SYSTEM_PYTHON=1`: Use system Python instead of creating new environment

**Runtime (in docker-compose.yml):**
- `UV_CACHE_DIR=/app/.cache/uv`: UV package manager cache
- `HOME=/app`: Home directory for all tools
- `XDG_CONFIG_HOME=/app/.config`: Standard config directory (XDG spec)
- `XDG_CACHE_HOME=/app/.cache`: Standard cache directory (XDG spec)
- `XDG_DATA_HOME=/app/.local/share`: Standard data directory (XDG spec)
- `MPLCONFIGDIR=/app/.config/matplotlib`: Matplotlib-specific config

These environment variables ensure **all tools** use writable directories inside `/app` for configuration, caching, and data storage, preventing permission errors.

### Marimo Command

```bash
uv run marimo edit --headless --host 0.0.0.0 --port 8080 --token --token-password=${MARIMO_TOKEN_PASSWORD}
```

- `--headless`: Don't auto-open browser (server-mode)
- `--host 0.0.0.0`: Accept connections from any interface
- `--port 8080`: Listen on port 8080
- `--token`: Enable authentication
- `--token-password`: Use environment variable for password

## References

- [Marimo Documentation](https://docs.marimo.io/)
- [Marimo Authentication Guide](https://docs.marimo.io/guides/deploying/authentication/)
- [Marimo Docker Deployment](https://docs.marimo.io/guides/deploying/deploying-docker/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
