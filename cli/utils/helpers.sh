#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail

trim() {
  local var="$*"
  # remove leading whitespace characters
  var="${var#"${var%%[![:space:]]*}"}"
  # remove trailing whitespace characters
  var="${var%"${var##*[![:space:]]}"}"
  printf '%s' "$var"
}
