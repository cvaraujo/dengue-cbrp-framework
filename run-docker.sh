#!/bin/bash
set -e

# ─── Configuration ───────────────────────────────────────────────
IMAGE_NAME="dengue-simheuristic"
CONTAINER_NAME="dengue-run"
RESULTS_DIR="$(pwd)/docker-results"

# ─── CLI flags ───────────────────────────────────────────────────
# Default: smart mode — build only if image is missing OR Dockerfile/requirements.txt
# changed since last build; always mount src/ (and a few code dirs) so editing Python
# files does not require a rebuild.
#   --rebuild        Force a full docker build (no cache reuse decisions).
#   --no-build       Never build; fail if image is missing.
#   --no-mount       Use the code baked into the image instead of mounting host code.
#   --rebuild-zip    Force regenerating cbrp-simheuristic.zip.
MODE="smart"
MOUNT_CODE=1
REBUILD_ZIP=0
for arg in "$@"; do
    case "$arg" in
        --rebuild)     MODE="rebuild" ;;
        --no-build)    MODE="no-build" ;;
        --no-mount)    MOUNT_CODE=0 ;;
        --rebuild-zip) REBUILD_ZIP=1 ;;
        -h|--help)
            cat <<EOF
Usage: $(basename "$0") [--rebuild] [--no-build] [--no-mount] [--rebuild-zip]
  (default)        Build only if missing/stale; mount src/ so code edits apply instantly.
  --rebuild        Force docker build.
  --no-build       Skip build; image must already exist.
  --no-mount       Run the code that is baked into the image (no live source mount).
  --rebuild-zip    Rebuild cbrp-simheuristic.zip even on fast path.
EOF
            exit 0 ;;
    esac
done

# ─── Pre-build: update simheuristic C++ zip ──────────────────────
# Only run when we actually plan to rebuild the image (the zip is consumed by Dockerfile).
needs_zip_rebuild=0
if [ "$MODE" = "rebuild" ] || [ "$REBUILD_ZIP" -eq 1 ]; then
    needs_zip_rebuild=1
fi

# Detect if image needs a build (smart mode)
image_exists=0
if docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    image_exists=1
fi

build_required=0
case "$MODE" in
    rebuild)  build_required=1 ;;
    no-build)
        if [ "$image_exists" -eq 0 ]; then
            echo "ERROR: --no-build requested but image '$IMAGE_NAME' is missing." >&2
            exit 1
        fi
        build_required=0
        ;;
    smart)
        if [ "$image_exists" -eq 0 ]; then
            build_required=1
        else
            # Rebuild if Dockerfile or requirements.txt are newer than the image.
            image_created_iso=$(docker image inspect -f '{{.Created}}' "$IMAGE_NAME" 2>/dev/null || echo "")
            if [ -n "$image_created_iso" ]; then
                image_created_ts=$(date -d "$image_created_iso" +%s 2>/dev/null || echo 0)
                for f in Dockerfile requirements.txt; do
                    if [ -f "$f" ]; then
                        f_ts=$(stat -c %Y "$f" 2>/dev/null || echo 0)
                        if [ "$f_ts" -gt "$image_created_ts" ]; then
                            echo "[smart] $f is newer than image; will rebuild."
                            build_required=1
                        fi
                    fi
                done
            fi
        fi
        ;;
esac

if [ "$build_required" -eq 1 ]; then
    needs_zip_rebuild=1
fi

if [ "$needs_zip_rebuild" -eq 1 ]; then
    echo "=== [1/4] Updating cbrp-simheuristic.zip from latest C++ source ==="
    if [ -f "build-simheuristic-zip.sh" ]; then
        bash build-simheuristic-zip.sh
    else
        echo "WARN: build-simheuristic-zip.sh not found, using existing zip"
    fi
else
    echo "=== [1/4] Skipping zip rebuild (use --rebuild-zip to force) ==="
fi

# ─── Clean up previous container if it exists ────────────────────
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "=== Removing previous container: $CONTAINER_NAME ==="
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
fi

# ─── Build Docker image (only when required) ─────────────────────
echo ""
if [ "$build_required" -eq 1 ]; then
    echo "=== [2/4] Building Docker image: $IMAGE_NAME ==="
    docker build -t "$IMAGE_NAME" .
else
    echo "=== [2/4] Skipping image build (using existing '$IMAGE_NAME'; pass --rebuild to force) ==="
fi

# ─── Prepare output directories ──────────────────────────────────
echo ""
echo "=== [3/4] Preparing output directories ==="
mkdir -p "$RESULTS_DIR"

# ─── Run experiments inside Docker ────────────────────────────────
echo ""
echo "=== [4/4] Running experiments inside Docker ==="
echo "    Results will be saved to: $RESULTS_DIR"
if [ "$MOUNT_CODE" -eq 1 ]; then
    echo "    Live-mounting host code (src/, simulation/, scripts/) — edits apply without rebuild."
else
    echo "    Using code baked into the image (--no-mount)."
fi
echo ""

# Build mount args. Always mount results-output. Mount source dirs in fast mode.
MOUNT_ARGS=( -v "$RESULTS_DIR:/app/results-output" )
if [ "$MOUNT_CODE" -eq 1 ]; then
    for d in src simulation scripts; do
        if [ -d "$d" ]; then
            MOUNT_ARGS+=( -v "$(pwd)/$d:/app/$d" )
        fi
    done
    if [ -f "requirements.txt" ]; then
        MOUNT_ARGS+=( -v "$(pwd)/requirements.txt:/app/requirements.txt:ro" )
    fi
fi

docker run --rm \
    --name "$CONTAINER_NAME" \
    --memory=28g \
    --cpus="$(nproc)" \
    "${MOUNT_ARGS[@]}" \
    "$IMAGE_NAME" \
    bash -c '
        set -e

        echo "[docker] Starting GAMA headless server..."
        /external-libs/gama/headless/gama-headless.sh -socket 6868 &
        GAMA_PID=$!

        echo "[docker] Waiting for GAMA to initialise (up to 10s)..."
        GAMA_READY=0
        for i in $(seq 1 10); do
            if curl -sf http://localhost:6868 >/dev/null 2>&1 || \
               (ss -tln 2>/dev/null | grep -q ":6868") || \
               [ -d /proc/$GAMA_PID ]; then
                if ss -tln 2>/dev/null | grep -q ":6868"; then
                    GAMA_READY=1
                    echo "[docker] GAMA is listening on port 6868 (after ${i}s)"
                    break
                fi
            fi
            if ! kill -0 $GAMA_PID 2>/dev/null; then
                echo "[docker] ERROR: GAMA process died during startup"
                exit 1
            fi
            sleep 1
        done

        if [ "$GAMA_READY" -eq 0 ]; then
            echo "[docker] WARNING: Could not confirm GAMA on port 6868 after 10s, proceeding anyway..."
        fi

        echo "[docker] Starting batch experiments..."
        python3 src/main-simheuristic.py batch docker /app/results-output/simheuristic_runs
        EXIT_CODE=$?

        if [ $EXIT_CODE -ne 0 ]; then
            echo "[docker] Experiments FAILED (exit code: $EXIT_CODE)."
        else
            echo "[docker] Experiments finished successfully."
        fi

        kill $GAMA_PID 2>/dev/null || true
        exit $EXIT_CODE
    '

echo ""
echo "=== Done! ==="
echo "Results saved to: $RESULTS_DIR/simheuristic_runs/"
