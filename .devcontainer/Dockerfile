FROM mcr.microsoft.com/devcontainers/universal:2-linux

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11vnc xfce4 novnc websockify dbus-x11 \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 \
    libxcb-xkb1 libxkbcommon-x11-0 libegl1 libgl1 libglx0 libgl1-mesa-dri \
    mesa-utils python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instalar PySide6
RUN pip install pyside6

# Redirección noVNC
RUN echo '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url=vnc.html" /></head><body><p>Redirigiendo...</p></body></html>' > /usr/share/novnc/index.html

# Permisos de directorios temporales
RUN mkdir -p /tmp/.X11-unix /tmp/.ICE-unix && chmod 1777 /tmp/.X11-unix /tmp/.ICE-unix
