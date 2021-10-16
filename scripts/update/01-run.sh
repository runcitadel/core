#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2021 Umbrel. https://getumbrel.com
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

set -euo pipefail

RELEASE=$1
CITADEL_ROOT=$2

./check-memory "${RELEASE}" "${CITADEL_ROOT}" "notfirstrun"

# Only used on Umbrel OS and Citadel OS
SD_CARD_CITADEL_ROOT="/sd-root${CITADEL_ROOT}"

echo
echo "======================================="
echo "=============== UPDATE ================"
echo "======================================="
echo "=========== Stage: Install ============"
echo "======================================="
echo

[[ -f "/etc/default/umbrel" ]] && source "/etc/default/umbrel"
[[ -f "/etc/default/citadel" ]] && source "/etc/default/citadel"

IS_MIGRATING=0
# Check if UMBREL_OS is set and CITADEL_OS is not
if [[ -z "${UMBREL_OS:-}" ]] && [[ -n "${CITADEL_OS:-}" ]]; then
    echo "Umbrel OS is being used..."
    echo "Upgrading to Citadel OS..."
    echo "export CITADEL_OS='0.0.1'" > /etc/default/citadel
    IS_MIGRATING=1
    CITADEL_OS='0.0.1'
    rm -rf "${CITADEL_ROOT}/electrs/db"
fi

# If the Citadel OS version is 0.0.1, fail
if [[ ! -z "${CITADEL_OS:-}" ]] && [[ "${CITADEL_OS}" == "0.0.1" ]]; then
    echo "Citadel OS version is 0.0.1. This is not supported."
  cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 50, "description": "We're sorry, but you tried installing the update on an unsupported OS. Please unplug your node and reflash the SD card with Citadel OS to continue.", "updateTo": "$RELEASE"}
EOF
    rm "${CITADEL_ROOT}/statuses/update-in-progress"
    docker stop bitcoin
    docker stop lnd
    docker stop electrs
    echo "We're sorry, but you tried installing the update on an unsupported OS. Please unplug your node and reflash the SD card with Citadel OS to continue."
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
    if  [[ -f "${SD_CARD_CITADEL_ROOT}/.umbrel" ]] || [[ -f "${SD_CARD_CITADEL_ROOT}/.citadel" ]]; then
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
        echo "ERROR: No Umbrel or Citadel installation found at SD root ${SD_CARD_CITADEL_ROOT}"
        echo "Skipping updating on SD Card..."
    fi

    # This makes sure systemd services are always updated (and new ones are enabled).
    UMBREL_SYSTEMD_SERVICES="${CITADEL_ROOT}/.citadel-${RELEASE}/scripts/citadel-os/services/*.service"
    for service_path in $UMBREL_SYSTEMD_SERVICES; do
      service_name=$(basename "${service_path}")
      install -m 644 "${service_path}" "/etc/systemd/system/${service_name}"
      systemctl enable "${service_name}"
    done
fi

cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 33, "description": "Configuring settings", "updateTo": "$RELEASE"}
EOF

# Checkout to the new release
cd "$CITADEL_ROOT"/.citadel-"$RELEASE"

# Configure new install
echo "Configuring new release"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 40, "description": "Configuring new release", "updateTo": "$RELEASE"}
EOF

PREV_ENV_FILE="$CITADEL_ROOT/.env"
BITCOIN_NETWORK="mainnet"
[[ -f "${PREV_ENV_FILE}" ]] && source "${PREV_ENV_FILE}"
PREV_ENV_FILE="${PREV_ENV_FILE}" NETWORK=$BITCOIN_NETWORK ./scripts/configure

# Pulling new containers
echo "Pulling new containers"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 50, "description": "Pulling new containers", "updateTo": "$RELEASE"}
EOF
docker compose pull

# Stop existing containers
echo "Stopping existing containers"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 60, "description": "Removing old containers", "updateTo": "$RELEASE"}
EOF
cd "$CITADEL_ROOT"
./scripts/stop

echo "Installing dependencies"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 61, "description": "Installing dependencies", "updateTo": "$RELEASE"}
EOF

# If apt is available, install python3-pip
if command -v apt >/dev/null 2>&1; then
  apt install -y python3-pip
fi

# If pip3 is available, install pyyaml and jsonschema
if command -v pip3 >/dev/null 2>&1; then
  pip3 install pyyaml jsonschema
fi

# Move Docker data dir to external storage now if this is an old install.
# This is only needed temporarily until all users have transitioned Docker to SSD.
DOCKER_DIR="/var/lib/docker"
MOUNT_POINT="/mnt/data"
EXTERNAL_DOCKER_DIR="${MOUNT_POINT}/docker"
if [[ ! -z "${UMBREL_OS:-}" ]] && [[ ! -d "${EXTERNAL_DOCKER_DIR}" ]]; then
  echo "Attempting to move Docker to external storage..."
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 62, "description": "Migrating Docker install to external storage", "updateTo": "$RELEASE"}
EOF

  echo "Stopping Docker service..."
  systemctl stop docker

  # Copy Docker data dir to external storage
  copy_docker_to_external_storage () {
    mkdir -p "${EXTERNAL_DOCKER_DIR}"
    cp  --recursive \
        --archive \
        --no-target-directory \
        "${DOCKER_DIR}" "${EXTERNAL_DOCKER_DIR}"
  }

  echo "Copying Docker data directory to external storage..."
  copy_docker_to_external_storage

  echo "Bind mounting external storage over local Docker data dir..."
  mount --bind "${EXTERNAL_DOCKER_DIR}" "${DOCKER_DIR}"

  # Ensure fs changes are registered
  sync
  sleep 1

  echo "Starting Docker service..."
  systemctl start docker
fi

# Stopping karen
echo "Stopping background daemon"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 65, "description": "Stopping background daemon", "updateTo": "$RELEASE"}
EOF
pkill -f "\./karen" || true

# Overlay home dir structure with new dir tree
echo "Overlaying $CITADEL_ROOT/ with new directory tree"
rsync --archive \
    --verbose \
    --include-from="$CITADEL_ROOT/.citadel-$RELEASE/scripts/update/.updateinclude" \
    --exclude-from="$CITADEL_ROOT/.citadel-$RELEASE/scripts/update/.updateignore" \
    --delete \
    "$CITADEL_ROOT"/.citadel-"$RELEASE"/ \
    "$CITADEL_ROOT"/

# Handle updating mysql conf for samourai-server app
samourai_app_mysql_conf="${CITADEL_ROOT}/apps/samourai-server/mysql/mysql-dojo.cnf"
samourai_data_mysql_conf="${CITADEL_ROOT}/app-data/samourai-server/mysql/mysql-dojo.cnf"
if [[ -f "${samourai_app_mysql_conf}" ]] && [[ -f "${samourai_data_mysql_conf}" ]]; then
  echo "Found samourai-server install, attempting to update DB configuration..."
  cp "${samourai_app_mysql_conf}" "${samourai_data_mysql_conf}"
fi

# Fix permissions
echo "Fixing permissions"
find "$CITADEL_ROOT" -path "$CITADEL_ROOT/app-data" -prune -o -exec chown 1000:1000 {} +
chmod -R 700 "$CITADEL_ROOT"/tor/data/*


echo "Updating installed apps"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 70, "description": "Updating installed apps", "updateTo": "$RELEASE"}
EOF
"${CITADEL_ROOT}/app/app-manager.py" update
for app in $("$CITADEL_ROOT/app/app-manager.py" ls-installed); do
  if [[ "${app}" != "" ]]; then
    echo "${app}..."
    app/app-manager.py compose "${app}" pull
  fi
done
wait

# On Citadel, the main network is now called Citadel
docker network rm umbrel_main_network || true

# Start updated containers
echo "Starting new containers"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 80, "description": "Starting new containers", "updateTo": "$RELEASE"}
EOF
cd "$CITADEL_ROOT"
./scripts/start
./scripts/app update-online || true

# Make Citadel OS specific post-update changes
if [[ ! -z "${CITADEL_OS:-}" ]]; then

  # Delete unused Docker images on Citadel OS
  echo "Deleting previous images"
  cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 90, "description": "Deleting previous images", "updateTo": "$RELEASE"}
EOF
  docker image prune --all --force
fi
