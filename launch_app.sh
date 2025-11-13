#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PORT=8505

if lsof -i :$PORT >/dev/null 2>&1; then
    echo "Error: Port $PORT is already in use. Close the app using it and try again."
    exit 1
fi

CONDA_SH="$SCRIPT_DIR/installation/miniconda3/etc/profile.d/conda.sh"
if [ -f "$CONDA_SH" ]; then
    source "$CONDA_SH"
else
    echo "Error: conda.sh not found at $CONDA_SH"
    exit 1
fi

if ! conda activate lafragua; then
    echo "Error: Could not activate the 'lafragua' environment"
    exit 1
fi

nohup streamlit run "$SCRIPT_DIR/app/home.py" --server.port $PORT --server.showEmailPrompt=False > "$SCRIPT_DIR/app/log.out" 2>&1 &
STREAMLIT_PID=$!

sleep 2
if ! ps -p $STREAMLIT_PID > /dev/null; then
    echo "Error: Streamlit failed to start. Check $SCRIPT_DIR/app/log.out for details."
    exit 1
fi

echo "✅ The app was successfully launched on port $PORT with PID $STREAMLIT_PID"
