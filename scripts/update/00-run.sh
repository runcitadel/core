#!/usr/bin/env bash
set -euo pipefail

RELEASE=$1
UMBREL_ROOT=$2

./check-memory "${RELEASE}" "${UMBREL_ROOT}" "firstrun"

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
echo "Citadel can only be installed on Umbrel 0.4.1 or later. If you're on an older version of Umbrel, please cancel the update now"
echo "by pressing CTRL+C."
sleep 5
echo "Thanks for joining us on the Citadel beta, we're installing the update."
sleep 3
echo "Please do not install an update from the dashboard if it asks you to, or you might go back to Umbrel."
sleep 3
echo "We're sorry aboutany other potential issues, we're working alpha 3 with more improvements."
sleep 3
echo "If you have any questions, please DM us on Twitter."
sleep 3
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

# Make sure any previous backup doesn't exist
if [[ -d "$UMBREL_ROOT"/.umbrel-backup ]]; then
    echo "Cannot install update. A previous backup already exists at $UMBREL_ROOT/.umbrel-backup"
    echo "This can only happen if the previous update installation wasn't successful"
    exit 1
fi

echo "Installing Umbrel $RELEASE at $UMBREL_ROOT"

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
    --include-from="$UMBREL_ROOT/.umbrel-$RELEASE/scripts/update/.updateinclude" \
    --exclude-from="$UMBREL_ROOT/.umbrel-$RELEASE/scripts/update/.updateignore" \
    "$UMBREL_ROOT"/ \
    "$UMBREL_ROOT"/.umbrel-backup/

echo "Successfully backed up to $UMBREL_ROOT/.umbrel-backup"
