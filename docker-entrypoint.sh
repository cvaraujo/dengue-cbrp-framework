#!/bin/bash
set -e

GAMA_HOME="/opt/gama/GAMA_1.9.2_Linux_with_JDK"
GAMA_HEADLESS="$GAMA_HOME/headless/gama-headless.sh"
GAMA_PORT="${GAMA_PORT:-6868}"

echo "[app] Iniciando GAMA headless..."
"$GAMA_HEADLESS" -socket "$GAMA_PORT" &
GAMA_PID=$!

echo "[app] Aguardando GAMA abrir porta $GAMA_PORT..."
for i in $(seq 1 60); do
    if ss -tln | grep -q ":$GAMA_PORT"; then
        echo "[app] GAMA pronto."
        break
    fi

    if ! kill -0 "$GAMA_PID" 2>/dev/null; then
        echo "[app] ERRO: processo do GAMA morreu durante a inicialização."
        exit 1
    fi

    sleep 1
done

if ! ss -tln | grep -q ":$GAMA_PORT"; then
    echo "[app] ERRO: GAMA não abriu a porta $GAMA_PORT."
    exit 1
fi

echo "[app] Executando Python..."
python /app/src/main.py
EXIT_CODE=$?

echo "[app] Encerrando GAMA..."
kill "$GAMA_PID" 2>/dev/null || true

exit $EXIT_CODE