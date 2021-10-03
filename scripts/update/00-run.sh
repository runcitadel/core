#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2020 Umbrel. https://getumbrel.com
# SPDX-FileCopyrightText: 2021 Citadel and contributors
#
# SPDX-License-Identifier: MIT

set -euo pipefail

RELEASE=$1
UMBREL_ROOT=$2

# Check if $UMBREL_ROOT/.umbrel-$RELEASE exists, if it does, rename it to $UMBREL_ROOT/.citadel-$RELEASE
if [ -d "$UMBREL_ROOT/.umbrel-$RELEASE" ]; then
    echo "Migrating from Umbrel..."
    echo "Your Umbrel will now be turned into a Citadel"
    echo "Please contact the Citadel team if anything goes wrong during the update"
    echo "Waiting 5 seconds, then the migration will start"
    sleep 5
    mv "$UMBREL_ROOT/.umbrel-$RELEASE" "$UMBREL_ROOT/.citadel-$RELEASE"
fi

# Functions which work like echo, but color the text red, green, and yellow
# respectively.
red() {
    echo -e "\033[31m$@\033[0m"
}
green() {
    echo -e "\033[32m$@\033[0m"
}
yellow() {
    echo -e "\033[33m$@\033[0m"
}

echo -n "Thanks for running "; yellow "#₿itcoin";
sleep 3

echo "This version of Citadel can only be installed on Umbrel 0.4.2 or existing Citadel installations. If you're on an older version of Umbrel, please cancel the update now"
echo "by pressing CTRL+C."
sleep 10
echo
green "Thanks for testing Citadel! The upgrade will start now."

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
if [[ -d "$UMBREL_ROOT"/.citadel-backup ]]; then
    echo "Cannot install update. A previous backup already exists at $UMBREL_ROOT/.citadel-backup"
    echo "This can only happen if the previous update installation wasn't successful"
    exit 1
fi

echo "Installing Citadel $RELEASE at $UMBREL_ROOT"

# Update status file
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 20, "description": "Backing up", "updateTo": "$RELEASE"}
EOF


# Backup
echo "Backing up existing directory tree"

rsync -av \
    --include-from="$UMBREL_ROOT/.citadel-$RELEASE/scripts/update/.updateinclude" \
    --exclude-from="$UMBREL_ROOT/.citadel-$RELEASE/scripts/update/.updateignore" \
    "$UMBREL_ROOT"/ \
    "$UMBREL_ROOT"/.citadel-backup/

echo "Successfully backed up to $UMBREL_ROOT/.citadel-backup"
