#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2021 Umbrel. https://getumbrel.com
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

set -euo pipefail

RELEASE=$1
UMBREL_ROOT=$2

./check-memory "${RELEASE}" "${UMBREL_ROOT}" "firstrun"

# Check if $UMBREL_ROOT/.umbrel-$RELEASE exists, if it does, rename it to $UMBREL_ROOT/.citadel-$RELEASE
if [ -d "$UMBREL_ROOT/.umbrel-$RELEASE" ]; then
    echo "Migrating from Umbrel..."
    echo "Your Umbrel will now be turned into a Citadel"
    echo "Please contact the Citadel team if anything goes wrong during the update"
    echo "Waiting 5 seconds, then the migration will start"
    sleep 5
    mv "$UMBREL_ROOT/.umbrel-$RELEASE" "$UMBREL_ROOT/.citadel-$RELEASE"
    touch "$UMBREL_ROOT/is-legacy-umbrel"
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
sleep 5

red "Please read the following notes carefully, they explain important details about bugs and other issues in the beta."
sleep 5
echo
echo "This version of Citadel can only be installed on Umbrel 0.4.2 or existing Citadel installatios. If you're on an older version of Umbrel, please cancel the update now"
echo "by pressing CTRL+C."
sleep 10
echo "Thanks for joining us on the Citadel beta! Your node will now be upgraded."
sleep 3
echo "Please do not install an update from the dashboard if it asks you to, or you might go back to Umbrel."
sleep 3
echo "We're sorry about any potential issues in this beta, if you experince problems or have questions, please DM us on Twitter."
sleep 5
echo "Waiting 10 seconds, if you want to cancel the update, press CTRL+C now."

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

# Check if $UMBREL_ROOT/.umbrel-$RELEASE exists, if it does, rename it to $UMBREL_ROOT/.citadel-$RELEASE
if [ -d "$UMBREL_ROOT/.umbrel-$RELEASE" ]; then
    echo "Migrating from Umbrel..."
    mv "$UMBREL_ROOT/.umbrel-$RELEASE" "$UMBREL_ROOT/.citadel-$RELEASE"
fi

# Make sure any previous backup doesn't exist
if [[ -d "$UMBREL_ROOT"/.citadel-backup ]]; then
    echo "Cannot install update. A previous backup already exists at $UMBREL_ROOT/.umbrel-backup"
    echo "This can only happen if the previous update installation wasn't successful"
    exit 1
fi

echo "Installing Citadel $RELEASE at $UMBREL_ROOT"

# Update status file
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 20, "description": "Backing up", "updateTo": "$RELEASE"}
EOF

# Fix permissions
echo "Fixing permissions"
find "$UMBREL_ROOT" -path "$UMBREL_ROOT/app-data" -prune -o -exec chown 1000:1000 {} +

# Backup
echo "Backing up existing directory tree"

rsync -av \
    --include-from="$UMBREL_ROOT/.citadel-$RELEASE/scripts/update/.updateinclude" \
    --exclude-from="$UMBREL_ROOT/.citadel-$RELEASE/scripts/update/.updateignore" \
    "$UMBREL_ROOT"/ \
    "$UMBREL_ROOT"/.citadel-backup/

echo "Successfully backed up to $UMBREL_ROOT/.citadel-backup"
