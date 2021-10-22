#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2020 Umbrel. https://getumbrel.com
# SPDX-FileCopyrightText: 2021 Citadel and contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -euo pipefail

RELEASE=$1
CITADEL_ROOT=$2

# Check if $CITADEL_ROOT/.umbrel-$RELEASE exists, if it does, rename it to $CITADEL_ROOT/.citadel-$RELEASE
if [ -d "$CITADEL_ROOT/.umbrel-$RELEASE" ]; then
    echo "Migrating from Umbrel..."
    echo "Your Umbrel will now be turned into a Citadel"
    echo "Please contact the Citadel team if anything goes wrong during the update"
    mv "$CITADEL_ROOT/.umbrel-$RELEASE" "$CITADEL_ROOT/.citadel-$RELEASE"
fi

echo
echo "======================================="
echo "=============== UPDATE ================"
echo "======================================="
echo "========= Stage: Pre-update ==========="
echo "======================================="
echo

# Stop karen early
pkill -f "\./karen" || true

# Make sure any previous backup doesn't exist
if [[ -d "$CITADEL_ROOT"/.citadel-backup ]]; then
    echo "Cannot install update. A previous backup already exists at $CITADEL_ROOT/.citadel-backup"
    echo "This can only happen if the previous update installation wasn't successful"
    exit 1
fi

echo "Installing Citadel $RELEASE at $CITADEL_ROOT"

# Update status file
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 20, "description": "Backing up", "updateTo": "$RELEASE"}
EOF


# Backup
echo "Backing up existing directory tree"

rsync -av \
    --include-from="$CITADEL_ROOT/.citadel-$RELEASE/scripts/update/.updateinclude" \
    --exclude-from="$CITADEL_ROOT/.citadel-$RELEASE/scripts/update/.updateignore" \
    "$CITADEL_ROOT"/ \
    "$CITADEL_ROOT"/.citadel-backup/

echo "Successfully backed up to $CITADEL_ROOT/.citadel-backup"
