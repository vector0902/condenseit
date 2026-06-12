#!/bin/bash
# (optional)
# Build cache helper: export/import Docker build cache to local directory
# Usage:
#   ./build-cache.sh export  - Export current build cache to /tmp/docker-cache
#   ./build-cache.sh import  - Import cache from /tmp/docker-cache
#   ./build-cache.sh cleanup - Remove cached files

CACHE_DIR="/tmp/docker-cache"
IMAGE_NAME="docker.cnb.cool/fjyaxax/condenseit"

case "$1" in
  export)
    echo "Exporting build cache to $CACHE_DIR ..."
    mkdir -p "$CACHE_DIR"
    # Save image tarball
    docker save "$IMAGE_NAME:latest" -o "$CACHE_DIR/condenseit-latest.tar" 2>/dev/null || true
    echo "Done. Cache saved."
    ;;
  import)
    echo "Importing build cache from $CACHE_DIR ..."
    if [ -f "$CACHE_DIR/condenseit-latest.tar" ]; then
      docker load -i "$CACHE_DIR/condenseit-latest.tar"
      echo "Done. Cache loaded."
    else
      echo "No cache found at $CACHE_DIR"
    fi
    ;;
  cleanup)
    echo "Cleaning up cache directory..."
    rm -rf "$CACHE_DIR"
    echo "Done."
    ;;
  *)
    echo "Usage: $0 {export|import|cleanup}"
    exit 1
    ;;
esac
