#!/bin/bash
set -e

# ─── Configuration ───────────────────────────────────────────────
IMAGE_NAME="dengue-simheuristic"
CONTAINER_NAME="dengue-run"
RESULTS_DIR="$(pwd)/docker-results"

# ─── Pre-build: update simheuristic C++ zip ──────────────────────
echo "=== [1/4] Updating cbrp-simheuristic.zip from latest C++ source ==="
if [ -f "build-simheuristic-zip.sh" ]; then
    bash build-simheuristic-zip.sh
else
    echo "WARN: build-simheuristic-zip.sh not found, using existing zip"
fi

# ─── Clean up previous container if it exists ────────────────────
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "=== Removing previous container: $CONTAINER_NAME ==="
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
fi

# ─── Build Docker image ──────────────────────────────────────────
echo ""
echo "=== [2/4] Building Docker image: $IMAGE_NAME ==="
docker build -t "$IMAGE_NAME" .

# ─── Prepare output directories ──────────────────────────────────
echo ""
echo "=== [3/4] Preparing output directories ==="
mkdir -p "$RESULTS_DIR"

# ─── Run experiments inside Docker ────────────────────────────────
echo ""
echo "=== [4/4] Running experiments inside Docker ==="
echo "    Results will be saved to: $RESULTS_DIR"
echo ""

docker run --rm \
    --name "$CONTAINER_NAME" \
    --memory=64g \
    --cpus="$(nproc)" \
    -v "$RESULTS_DIR:/app/results-output" \
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
