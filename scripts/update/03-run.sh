#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2020 Umbrel. https://getumbrel.com
# SPDX-FileCopyrightText: 2021 Citadel and contributors
#
# SPDX-License-Identifier: MIT

set -euo pipefail

RELEASE=$1
CITADEL_ROOT=$2

echo
echo "======================================="
echo "=============== UPDATE ================"
echo "======================================="
echo "=========== Stage: Success ============"
echo "======================================="
echo

# Cleanup
echo "Removing backup"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 95, "description": "Removing backup"}
EOF
[[ -d "$CITADEL_ROOT"/.umbrel-backup ]] && rm -rf "$CITADEL_ROOT"/.umbrel-backup

echo "Successfully installed Citadel $RELEASE"
cat <<EOF > "$CITADEL_ROOT"/statuses/update-status.json
{"state": "success", "progress": 100, "description": "Successfully installed Citadel $RELEASE", "updateTo": ""}
EOF
