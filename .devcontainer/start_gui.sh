#!/bin/bash
# chmod +x .devcontainer/start_gui.sh .devcontainer/restart_app.sh && .devcontainer/start_gui.sh
# .devcontainer/start_gui.sh
# .devcontainer/restart_app.sh
set -eo pipefail

# Ir a la raíz del proyecto (donde está main.py)
cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)

# ==============================================================================
# LIMPIEZA ROBUSTA: Asegurar que Xvfb muera antes de limpiar sockets
# ==============================================================================
echo "🧹 Limpiando procesos anteriores..."
pkill -9 -f "Xvfb :99" 2>/dev/null || true
pkill -9 x11vnc xfce4-session websockify 2>/dev/null || true
fuser -k 6080/tcp 2>/dev/null || true
fuser -k 5900/tcp 2>/dev/null || true

echo "⏳ Esperando a que Xvfb se cierre..."
timeout=5
while pgrep -x Xvfb > /dev/null; do
    sleep 0.5
    timeout=$((timeout - 1))
    if [ $timeout -le 0 ]; then
        echo "⚠️ Xvfb no respondió, forzando limpieza..."
        break
    fi
done

sudo rm -f /tmp/.X99-lock
sudo rm -rf /tmp/.X11-unix/X99 /tmp/.ICE-unix
sleep 1

# ==============================================================================
# BOMPROOF: Auto-instalar dependencias del sistema si faltan
# ==============================================================================
NEEDS_INSTALL=false
if ! command -v Xvfb &> /dev/null; then NEEDS_INSTALL=true; fi
if ! dpkg -s libxcb-cursor0 &> /dev/null; then NEEDS_INSTALL=true; fi

if [ "$NEEDS_INSTALL" = true ]; then
    echo "📦 Faltan paquetes del sistema. Instalando..."
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        xvfb xfce4 xfce4-goodies x11vnc novnc websockify \
        dbus-x11 light-locker polkitd \
        libxcb-cursor0 libxcb-cursor-dev \
        libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
        libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
        libxcb-shape0 libxcb-sync1 libxcb-util1 libxcb-xfixes0 \
        libxcb-xkb1 libxkbcommon-x11-0 \
        libgl1 libegl1 libglx-mesa0 libegl-mesa0 \
        libglib2.0-0 libfontconfig1 libdbus-1-3
    echo "✅ Paquetes del sistema instalados."
fi

if ! command -v websockify &> /dev/null; then
    echo "📦 Instalando websockify con pip..."
    pip install websockify
fi

# ==============================================================================
# FIX CRÍTICO: Recrear los sockets de X11 con permisos exactos (Sticky Bit 1777)
# ==============================================================================
echo "🔧 Preparando sockets X11 e ICE..."
sudo mkdir -p /tmp/.X11-unix /tmp/.ICE-unix
sudo chmod 1777 /tmp/.X11-unix /tmp/.ICE-unix

echo "🧵 Verificando dbus-daemon..."
if [ -f /run/dbus/pid ]; then
    if ! kill -0 "$(cat /run/dbus/pid)" 2>/dev/null; then
        sudo rm -f /run/dbus/pid
    fi
fi
if ! pgrep -x dbus-daemon > /dev/null; then
    sudo dbus-daemon --system --fork 2>/dev/null || true
fi

# ==============================================================================
# FIX DE ESTABILIDAD: Deshabilitar servicios de XFCE que crashean en contenedores
# ==============================================================================
echo "🛡️ Deshabilitando servicios innecesarios del contenedor..."
mkdir -p ~/.config/autostart
echo "[Desktop Entry]
Type=Application
Name=Noop
Exec=/bin/true" > ~/.config/autostart/light-locker.desktop

echo "[Desktop Entry]
Type=Application
Name=Noop
Exec=/bin/true" > ~/.config/autostart/polkit-gnome-authentication-agent-1.desktop

# ==============================================================================
# Variables de entorno
# ==============================================================================
export DISPLAY=:99
export LIBGL_ALWAYS_SOFTWARE=1
export PULSE_SERVER=

# === FIX CRÍTICO: Qt xcb plugin ===
export QT_QPA_PLATFORM=xcb
export QT_QPA_PLATFORM_PLUGIN_PATH=$(python3 -c "import PySide6; import os; print(os.path.join(os.path.dirname(PySide6.__file__), 'plugins', 'platforms'))" 2>/dev/null || python3 -c "import PyQt6; import os; print(os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'plugins', 'platforms'))" 2>/dev/null || echo "")
export QT_DEBUG_PLUGINS=0

echo "🖥️ Iniciando Xvfb..."
Xvfb :99 -screen 0 1280x720x24 +extension GLX +render -noreset &

# Espera activa a que el socket de X11 realmente exista
echo "⏳ Esperando a que Xvfb esté listo..."
timeout=15
while [ ! -S /tmp/.X11-unix/X99 ]; do
    sleep 0.5
    timeout=$((timeout - 1))
    if [ $timeout -le 0 ]; then
        echo "❌ Error crítico: Xvfb no pudo iniciar el socket."
        exit 1
    fi
done

echo "🪟 Iniciando XFCE..."
startxfce4 > /dev/null 2>&1 &

echo "📡 Iniciando x11vnc..."
mkdir -p ~/.vnc
x11vnc -display :99 \
       -xkb \
       -nopw \
       -shared \
       -noxdamage \
       -forever \
       -bg \
       -o ~/.vnc/x11vnc.log \
       -rfbport 5900

# Espera activa a que el puerto VNC esté escuchando
echo "⏳ Esperando a que x11vnc esté listo..."
timeout=15
while ! fuser 5900/tcp >/dev/null 2>&1; do
    sleep 0.5
    timeout=$((timeout - 1))
    if [ $timeout -le 0 ]; then
        echo "❌ Error crítico: x11vnc no pudo iniciar."
        exit 1
    fi
done

echo "🌐 Iniciando websockify en puerto 6080..."
websockify --web=/usr/share/novnc 6080 localhost:5900 > /dev/null 2>&1 &

# Espera activa a que websockify esté listo
echo "⏳ Esperando a que websockify esté listo..."
timeout=15
while ! fuser 6080/tcp >/dev/null 2>&1; do
    sleep 0.5
    timeout=$((timeout - 1))
    if [ $timeout -le 0 ]; then
        echo "❌ Error crítico: websockify no pudo iniciar."
        exit 1
    fi
done

echo "🚀 Lanzando main.py..."
# No redirigir stderr para poder ver errores de Qt
python3 main.py 2>&1 | tee /tmp/main_app.log &
APP_PID=$!

# Dar unos segundos y verificar que sigue vivo
sleep 3
if ! kill -0 $APP_PID 2>/dev/null; then
    echo "❌ main.py crasheó. Últimas líneas del log:"
    tail -30 /tmp/main_app.log
    exit 1
fi

if command -v gp &> /dev/null; then
    gp preview --external "$(gp url 6080)/" > /dev/null 2>&1 &
fi

echo ""
echo "✅ Entorno listo y bombproof - Tu aplicación está corriendo"