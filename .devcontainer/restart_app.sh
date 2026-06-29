#!/bin/bash

# Ir a la raíz del proyecto
cd "$(dirname "$0")/.."

echo "🔄 Matando main.py anterior..."
pkill -f "python3 main.py" 2>/dev/null || true
sleep 1

echo "🚀 Lanzando nueva versión de main.py..."
export DISPLAY=:99
python3 main.py &

echo "✅ main.py reiniciado. Revisa la ventana en el navegador."
