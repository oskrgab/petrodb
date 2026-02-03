#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read DEPLOY_TARGET from .env file
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    DEPLOY_TARGET=$(grep -E '^DEPLOY_TARGET=' "$SCRIPT_DIR/.env" | cut -d'=' -f2-)
else
    echo "Error: .env file not found in $SCRIPT_DIR"
    exit 1
fi

if [[ -z "$DEPLOY_TARGET" ]]; then
    echo "Error: DEPLOY_TARGET not set in .env"
    exit 1
fi

# Create target directory if it doesn't exist
mkdir -p "$DEPLOY_TARGET"

# Sync parquet directory contents to target
rsync -av --delete "$SCRIPT_DIR/parquet/" "$DEPLOY_TARGET/"

echo "Deployed to $DEPLOY_TARGET"
