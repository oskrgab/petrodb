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

# Build the Landing (ADR-0010). It copies the schema documents in from
# parquet/ and prerenders every page into site/build.
# Run from site/ so corepack picks the pnpm version pinned in its package.json.
if command -v pnpm >/dev/null; then PNPM=(pnpm); else PNPM=(corepack pnpm); fi
(
    cd "$SCRIPT_DIR/site"
    "${PNPM[@]}" install --frozen-lockfile
    "${PNPM[@]}" build
)

# Publish the data, then the built Landing over it. The dev host serves both
# from one root, so the Landing's pages replace the data tree's old index.html.
# --delete on the first pass prunes stale files, the previous build included.
rsync -av --delete "$SCRIPT_DIR/parquet/" "$DEPLOY_TARGET/"
rsync -av "$SCRIPT_DIR/site/build/" "$DEPLOY_TARGET/"

echo "Deployed to $DEPLOY_TARGET"
