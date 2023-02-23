#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2020 Umbrel. https://getumbrel.com
# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail

RELEASE=$1
CITADEL_ROOT=$2

# Only used on Citadel OS
SD_CARD_CITADEL_ROOT="/sd-root${CITADEL_ROOT}"

echo
echo "======================================="
echo "=============== UPDATE ================"
echo "======================================="
echo "=========== Stage: Install ============"
echo "======================================="
echo

[[ -f "/etc/default/citadel" ]] && source "/etc/default/citadel"

# If ${CITADEL_ROOT}/c-lightning exists, fail
if [[ -d "${CITADEL_ROOT}/c-lightning" ]]; then
    echo "This update is not compatible with the c-lightning beta."
    cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 1, "description": "This update is not compatible with c-lightning", "updateTo": "$RELEASE"}
EOF
    exit 1
fi

# Make Citadel OS specific updates
if [[ ! -z "${CITADEL_OS:-}" ]]; then
    echo
    echo "============================================="
    echo "Installing on Citadel OS $CITADEL_OS"
    echo "============================================="
    echo
    
    # Update SD card installation
    if  [[ -f "${SD_CARD_CITADEL_ROOT}/.citadel" ]]; then
        echo "Replacing ${SD_CARD_CITADEL_ROOT} on SD card with the new release"
        rsync --archive \
            --verbose \
            --include-from="${CITADEL_ROOT}/.citadel-${RELEASE}/scripts/update/.updateinclude" \
            --exclude-from="${CITADEL_ROOT}/.citadel-${RELEASE}/scripts/update/.updateignore" \
            --delete \
            "${CITADEL_ROOT}/.citadel-${RELEASE}/" \
            "${SD_CARD_CITADEL_ROOT}/"

        echo "Fixing permissions"
        chown -R 1000:1000 "${SD_CARD_CITADEL_ROOT}/"
    else
        echo "ERROR: No Citadel installation found at SD root ${SD_CARD_CITADEL_ROOT}"
        echo "Skipping updating on SD Card..."
    fi

    # This makes sure systemd services are always updated (and new ones are enabled).
    CITADEL_SYSTEMD_SERVICES="${CITADEL_ROOT}/.citadel-${RELEASE}/scripts/citadel-os/services/*.service"
    for service_path in $CITADEL_SYSTEMD_SERVICES; do
      service_name=$(basename "${service_path}")
      install -m 644 "${service_path}" "/etc/systemd/system/${service_name}"
      systemctl enable "${service_name}"
    done

    # Apply config.txt changes
    curl https://raw.githubusercontent.com/runcitadel/os/main/stage1/00-boot-files/files/config.txt > /boot/config.txt

    echo "source ~/citadel/setenv" | tee -a /home/citadel/.bashrc

    sudo apt install -y python3-semver
fi

# Help migration from earlier versions
mv "$CITADEL_ROOT/db/umbrel-seed" "$CITADEL_ROOT/db/citadel-seed" || true

cd "$CITADEL_ROOT"

# Stopping karen
echo "Stopping background daemon"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 55, "description": "Stopping background daemon", "updateTo": "$RELEASE"}
EOF
pkill -f "\./karen" || true

echo "Stopping installed apps"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 60, "description": "Stopping installed apps", "updateTo": "$RELEASE"}
EOF
./scripts/app stop installed || true

# Stop old containers
echo "Stopping old containers"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 67, "description": "Stopping old containers", "updateTo": "$RELEASE"}
EOF
./scripts/stop || true

# Overlay home dir structure with new dir tree
echo "Overlaying $CITADEL_ROOT/ with new directory tree"
rsync --archive \
    --verbose \
    --include-from="$CITADEL_ROOT/.citadel-$RELEASE/scripts/update/.updateinclude" \
    --exclude-from="$CITADEL_ROOT/.citadel-$RELEASE/scripts/update/.updateignore" \
    --delete \
    "$CITADEL_ROOT"/.citadel-"$RELEASE"/ \
    "$CITADEL_ROOT"/

# Fix permissions
echo "Fixing permissions"
find "$CITADEL_ROOT" -path "$CITADEL_ROOT/app-data" -prune -o -exec chown 1000:1000 {} + || true
chmod -R 700 "$CITADEL_ROOT"/tor/data/* || true

# Start updated containers
echo "Starting new containers"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 80, "description": "Starting new containers", "updateTo": "$RELEASE"}
EOF
cd "$CITADEL_ROOT"
./scripts/start || true


cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "success", "progress": 100, "description": "Successfully installed Citadel $RELEASE", "updateTo": ""}
EOF

# Make Citadel OS specific post-update changes
if [[ ! -z "${CITADEL_OS:-}" ]]; then
  # Delete unused Docker images on Citadel OS
  echo "Deleting previous images"
  docker image prune --all --force
fi
