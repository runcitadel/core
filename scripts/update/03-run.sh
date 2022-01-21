#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2020 Umbrel. https://getumbrel.com
# SPDX-FileCopyrightText: 2021 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

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
[[ -d "$CITADEL_ROOT"/.citadel-backup ]] && rm -rf "$CITADEL_ROOT"/.citadel-backup

echo "Successfully installed Citadel $RELEASE"
echo "Thank you for using Citadel!"
