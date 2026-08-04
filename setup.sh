#!/bin/bash
# Set up the Camera Label Dashboard + service on a stock Neoracer.
#
# From your laptop, on the same network as the car:
#   scp -r neoracer_camlabel racecar@<car-ip>:~/camlabel
#   ssh racecar@<car-ip> 'bash ~/camlabel/setup.sh'
#
# Installs neoracer-camlabel.service, enables it at boot, and starts it.
# Dashboard comes up at http://<car-ip>:8082. Idempotent: safe to re-run.
#
# Needs nothing beyond the stock image: ROS Humble at /opt/ros/humble, the
# driver workspace at /home/racecar/ros2_ws, and the racecar user.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST=/home/racecar/camlabel
SVC=neoracer-camlabel.service

# `bash setup.sh disable` stops the service and keeps it off across boots.
# `bash setup.sh enable` turns it back on. No arguments installs as usual.
if [[ "${1:-}" == "disable" ]]; then
    sudo systemctl disable --now "$SVC"
    echo "$SVC stopped and disabled. It will not start at boot."
    echo "Re-enable with: bash setup.sh enable"
    exit 0
elif [[ "${1:-}" == "enable" ]]; then
    sudo systemctl enable --now "$SVC"
    echo "$SVC enabled and started."
    exit 0
fi

# The service unit expects the files at $DEST. If the script runs from
if [[ "$SCRIPT_DIR" != "$DEST" ]]; then
    mkdir -p "$DEST"
    cp "$SCRIPT_DIR/camlabel.py" "$SCRIPT_DIR/camlabel.html" "$SCRIPT_DIR/$SVC" \
       "$SCRIPT_DIR/setup.sh" "$DEST/"
    [[ -f "$DEST/camlabel.yaml" ]] || cp "$SCRIPT_DIR/camlabel.yaml" "$DEST/"
fi

if ! cmp -s "$DEST/$SVC" "/etc/systemd/system/$SVC" 2>/dev/null; then
    sudo install -m 0644 "$DEST/$SVC" "/etc/systemd/system/$SVC"
    sudo systemctl daemon-reload
    echo "  $SVC: installed"
fi

sudo systemctl enable --now "$SVC" 2>/dev/null
sudo systemctl restart "$SVC"    # pick up file changes on re-run

sleep 3
systemctl is-active --quiet "$SVC" || { echo "$SVC failed to start:"; systemctl status "$SVC" --no-pager | tail -5; exit 1; }
echo "Camera Label Dashboard running: http://$(hostname -I | awk '{print $1}'):8082"
