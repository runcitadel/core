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

IS_MIGRATING=0

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

    sudo apt install -y python3-dacite python3-semver
fi

# Help migration from earlier versions
mv "$CITADEL_ROOT/db/umbrel-seed" "$CITADEL_ROOT/db/citadel-seed" || true

# Checkout to the new release
cd "$CITADEL_ROOT"/.citadel-"$RELEASE"

# Configure new install
echo "Configuring new release"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 40, "description": "Configuring new release", "updateTo": "$RELEASE"}
EOF

./scripts/configure || true

# Pulling new containers
echo "Pulling new containers"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 50, "description": "Pulling new containers", "updateTo": "$RELEASE"}
EOF
docker compose -f docker-compose.citadel.yml pull

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
cd "$CITADEL_ROOT"
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
find "$CITADEL_ROOT" -path "$CITADEL_ROOT/app-data" -prune -o -exec chown 1000:1000 {} +
chmod -R 700 "$CITADEL_ROOT"/tor/data/*

cd "$CITADEL_ROOT"
echo "Updating installed apps"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 70, "description": "Updating installed apps", "updateTo": "$RELEASE"}
EOF
"${CITADEL_ROOT}/scripts/app" --invoked-by-configure update
for app in $("$CITADEL_ROOT/scripts/app" ls-installed); do
  if [[ "${app}" != "" ]]; then
    echo "${app}..."
    "${CITADEL_ROOT}/scripts/app" compose "${app}" pull
  fi
done
wait

# If CITADEL_ROOT doesn't contain services/installed.json, then put '["electrs"]' into it.
# This is to ensure that the 0.5.0 update doesn't remove electrs.
if [[ ! -f "${CITADEL_ROOT}/services/installed.json" ]]; then
  echo '["electrs"]' > "${CITADEL_ROOT}/services/installed.json"
fi

# Start updated containers
echo "Starting new containers"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 80, "description": "Starting new containers", "updateTo": "$RELEASE"}
EOF
cd "$CITADEL_ROOT"
./scripts/start

cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "success", "progress": 100, "description": "Successfully installed Citadel $RELEASE", "updateTo": ""}
EOF

# Make Citadel OS specific post-update changes
if [[ ! -z "${CITADEL_OS:-}" ]]; then
  # Delete unused Docker images on Citadel OS
  echo "Deleting previous images"
  docker image prune --all --force
fi
