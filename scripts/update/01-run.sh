#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2021 Umbrel. https://getumbrel.com
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

set -euo pipefail

RELEASE=$1
UMBREL_ROOT=$2

./check-memory "${RELEASE}" "${UMBREL_ROOT}" "notfirstrun"

# Only used on Umbrel OS and Citadel OS
SD_CARD_UMBREL_ROOT="/sd-root${UMBREL_ROOT}"

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
if [[ -z "$UMBREL_OS" ]] && [[ -n "$CITADEL_OS" ]]; then
    echo "Umbrel OS is being used..."
    echo "Upgrading to Citadel OS..."
    echo "export CITADEL_OS='0.0.1'" > /etc/default/citadel
    IS_MIGRATING=1
    CITADEL_OS='0.0.1'
fi

if [[ -f "$UMBREL_ROOT/is-legacy-umbrel" ]]; then
# If this file exists, we are migrating
  IS_MIGRATING=1
fi

# Make Umbrel OS specific updates
if [[ ! -z "${CITADEL_OS:-}" ]]; then
    echo
    echo "============================================="
    echo "Installing on Citadel OS $CITADEL_OS"
    echo "============================================="
    echo
    
    # Update SD card installation
    if  [[ -f "${SD_CARD_UMBREL_ROOT}/.umbrel" ]] || [[ -f "${SD_CARD_UMBREL_ROOT}/.citadel" ]]; then
        echo "Replacing ${SD_CARD_UMBREL_ROOT} on SD card with the new release"
        rsync --archive \
            --verbose \
            --include-from="${UMBREL_ROOT}/.citadel-${RELEASE}/scripts/update/.updateinclude" \
            --exclude-from="${UMBREL_ROOT}/.citadel-${RELEASE}/scripts/update/.updateignore" \
            --delete \
            "${UMBREL_ROOT}/.citadel-${RELEASE}/" \
            "${SD_CARD_UMBREL_ROOT}/"

        echo "Fixing permissions"
        chown -R 1000:1000 "${SD_CARD_UMBREL_ROOT}/"
    else
        echo "ERROR: No Umbrel or Citadel installation found at SD root ${SD_CARD_UMBREL_ROOT}"
        echo "Skipping updating on SD Card..."
    fi

    # This makes sure systemd services are always updated (and new ones are enabled).
    UMBREL_SYSTEMD_SERVICES="${UMBREL_ROOT}/.umbrel-${RELEASE}/scripts/umbrel-os/services/*.service"
    for service_path in $UMBREL_SYSTEMD_SERVICES; do
      service_name=$(basename "${service_path}")
      install -m 644 "${service_path}" "/etc/systemd/system/${service_name}"
      systemctl enable "${service_name}"
    done
fi

cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 33, "description": "Configuring settings", "updateTo": "$RELEASE"}
EOF

# Checkout to the new release
cd "$UMBREL_ROOT"/.umbrel-"$RELEASE"

# Configure new install
echo "Configuring new release"
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 40, "description": "Configuring new release", "updateTo": "$RELEASE"}
EOF

PREV_ENV_FILE="$UMBREL_ROOT/.env"
BITCOIN_NETWORK="mainnet"
[[ -f "${PREV_ENV_FILE}" ]] && source "${PREV_ENV_FILE}"
PREV_ENV_FILE="${PREV_ENV_FILE}" NETWORK=$BITCOIN_NETWORK ./scripts/configure

# Pulling new containers
echo "Pulling new containers"
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 50, "description": "Pulling new containers", "updateTo": "$RELEASE"}
EOF
docker compose pull

echo "Updating installed apps"
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 60, "description": "Updating installed apps", "updateTo": "$RELEASE"}
EOF
"${UMBREL_ROOT}/app/app-manager.py" update
for app in $("$UMBREL_ROOT/scripts/app" ls-installed); do
  if [[ "${app}" != "" ]]; then
    echo "${app}..."
    scripts/app compose "${app}" pull &
  fi
done
wait

# Stop existing containers
echo "Stopping existing containers"
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 70, "description": "Removing old containers", "updateTo": "$RELEASE"}
EOF
cd "$UMBREL_ROOT"
./scripts/stop

# Move Docker data dir to external storage now if this is an old install.
# This is only needed temporarily until all users have transitioned Docker to SSD.
DOCKER_DIR="/var/lib/docker"
MOUNT_POINT="/mnt/data"
EXTERNAL_DOCKER_DIR="${MOUNT_POINT}/docker"
if [[ ! -z "${UMBREL_OS:-}" ]] && [[ ! -d "${EXTERNAL_DOCKER_DIR}" ]]; then
  echo "Attempting to move Docker to external storage..."
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 72, "description": "Migrating Docker install to external storage", "updateTo": "$RELEASE"}
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

# Overlay home dir structure with new dir tree
echo "Overlaying $UMBREL_ROOT/ with new directory tree"
rsync --archive \
    --verbose \
    --include-from="$UMBREL_ROOT/.citadel-$RELEASE/scripts/update/.updateinclude" \
    --exclude-from="$UMBREL_ROOT/.citadel-$RELEASE/scripts/update/.updateignore" \
    --delete \
    "$UMBREL_ROOT"/.umbrel-"$RELEASE"/ \
    "$UMBREL_ROOT"/

# Handle updating mysql conf for samourai-server app
samourai_app_mysql_conf="${UMBREL_ROOT}/apps/samourai-server/mysql/mysql-dojo.cnf"
samourai_data_mysql_conf="${UMBREL_ROOT}/app-data/samourai-server/mysql/mysql-dojo.cnf"
if [[ -f "${samourai_app_mysql_conf}" ]] && [[ -f "${samourai_data_mysql_conf}" ]]; then
  echo "Found samourai-server install, attempting to update DB configuration..."
  cp "${samourai_app_mysql_conf}" "${samourai_data_mysql_conf}"
fi

# Fix permissions
echo "Fixing permissions"
find "$UMBREL_ROOT" -path "$UMBREL_ROOT/app-data" -prune -o -exec chown 1000:1000 {} +
chmod -R 700 "$UMBREL_ROOT"/tor/data/*

# Killing karen
echo "Killing background daemon"
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 75, "description": "Killing background daemon", "updateTo": "$RELEASE"}
EOF
pkill -f "\./karen"

# Start updated containers
# If we're migrating (IS_MIGRATING is set to 1, not 0) then we reset the electrs data
if [[ "${IS_MIGRATING}" == "1" ]]; then
  echo "Resetting electrs"
  cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 78, "description": "Resetting electrs", "updateTo": "$RELEASE"}
EOF
  rm -rf "$UMBREL_ROOT/electrs/*"
fi

# Start updated containers
echo "Starting new containers"
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 80, "description": "Starting new containers", "updateTo": "$RELEASE"}
EOF
cd "$UMBREL_ROOT"
./scripts/start

# Make Citadel OS specific post-update changes
if [[ ! -z "${CITADEL_OS:-}" ]]; then

  # Delete unused Docker images on Citadel OS
  echo "Deleting previous images"
  cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 90, "description": "Deleting previous images", "updateTo": "$RELEASE"}
EOF
  docker image prune --all --force
fi
