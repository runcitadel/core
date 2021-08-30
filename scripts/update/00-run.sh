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

echo -n "Running "; yellow "₿itcoin";
sleep 5

red "Please read the following notes carefully, as it explains details about bugs and other issues in the beta."
sleep 7
echo
echo "Thanks for joining us on the Citadel beta, we're installing the update."
sleep 3
echo "There is an ongoing issue with the blocks not being displayed on the dashboard, please be patient, a fix is in development."
sleep 3
echo "Meanwhile, you can use the mempool app to check if the blocks are still being synced."
sleep 3
echo "Also, please do NOT install an update from the dashboard if it asks you to, or you might go back to Umbrel."
sleep 3
echo "We're sorry for all these issues, and beta 2 next week will fix most of them and include updated apps."
sleep 3
echo "If you have any questions, please DM us on Twitter."
sleep 3
echo "Waiting 60 seconds, if you want to cancel the update, turn your node off using the dashboard now"

sleep 60
echo
green "Thanks for testing Citadel! The update will start now."

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
