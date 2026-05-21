#!/bin/bash
set -e

# ─── Configuration ───────────────────────────────────────────────
IMAGE_NAME="dengue-simulation"
CONTAINER_NAME="dengue-sim-run"
RESULTS_DIR="$(pwd)/docker-results"

# Default simulation parameters (override via env vars or CLI args)
OUTPUT_FOLDER="${1:-/app/results-output/simulation_metrics/}"
PREV_DATE="${2:-2017-01-01}"
START_DATE="${3:-2017-01-08}"

# ─── Clean up previous container if it exists ────────────────────
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "=== Removing previous container: $CONTAINER_NAME ==="
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
fi

# ─── Build Docker image ──────────────────────────────────────────
echo ""
echo "=== [1/3] Building Docker image: $IMAGE_NAME ==="
docker build -f container-simulation-only/Dockerfile -t "$IMAGE_NAME" .

# ─── Prepare output directories ──────────────────────────────────
echo ""
echo "=== [2/3] Preparing output directories ==="
mkdir -p "$RESULTS_DIR"

# ─── Run simulation inside Docker ────────────────────────────────
echo ""
echo "=== [3/3] Running simulation inside Docker ==="
echo "    Output folder: $OUTPUT_FOLDER"
echo "    Prev date:     $PREV_DATE"
echo "    Start date:    $START_DATE"
echo "    Results dir:   $RESULTS_DIR"
echo ""

docker run --rm \
    --name "$CONTAINER_NAME" \
    --memory=64g \
    --cpus="$(nproc)" \
    -v "$RESULTS_DIR:/app/results-output" \
    "$IMAGE_NAME" \
    bash -c "
        set -e

        echo '[docker] Starting GAMA headless server...'
        /external-libs/gama/headless/gama-headless.sh -socket 6868 &
        GAMA_PID=\$!

        echo '[docker] Waiting for GAMA to initialise (up to 10s)...'
        GAMA_READY=0
        for i in \$(seq 1 10); do
            if ss -tln 2>/dev/null | grep -q ':6868'; then
                GAMA_READY=1
                echo \"[docker] GAMA is listening on port 6868 (after \${i}s)\"
                break
            fi
            if ! kill -0 \$GAMA_PID 2>/dev/null; then
                echo '[docker] ERROR: GAMA process died during startup'
                exit 1
            fi
            sleep 1
        done

        if [ \"\$GAMA_READY\" -eq 0 ]; then
            echo '[docker] WARNING: Could not confirm GAMA on port 6868 after 10s, proceeding anyway...'
        fi

        echo '[docker] Starting simulation (main.py)...'
        python3 src/main.py $OUTPUT_FOLDER $PREV_DATE $START_DATE
        EXIT_CODE=\$?

        if [ \$EXIT_CODE -ne 0 ]; then
            echo \"[docker] Simulation FAILED (exit code: \$EXIT_CODE).\"
        else
            echo '[docker] Simulation finished successfully.'
        fi

        kill \$GAMA_PID 2>/dev/null || true
        exit \$EXIT_CODE
    "

echo ""
echo "=== Done! ==="
echo "Results saved to: $RESULTS_DIR"
