#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2020 Umbrel. https://getumbrel.com
# SPDX-FileCopyrightText: 2021 Citadel and contributors
#
# SPDX-License-Identifier: MIT

set -euo pipefail

RELEASE=$1
UMBREL_ROOT=$2

echo
echo "======================================="
echo "=============== UPDATE ================"
echo "======================================="
echo "=========== Stage: Success ============"
echo "======================================="
echo

# Cleanup
echo "Removing backup"
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 95, "description": "Removing backup"}
EOF
[[ -d "$UMBREL_ROOT"/.umbrel-backup ]] && rm -rf "$UMBREL_ROOT"/.umbrel-backup

echo "Successfully installed Umbrel $RELEASE"
cat <<EOF > "$UMBREL_ROOT"/statuses/update-status.json
{"state": "success", "progress": 100, "description": "Successfully installed Umbrel $RELEASE", "updateTo": ""}
EOF
