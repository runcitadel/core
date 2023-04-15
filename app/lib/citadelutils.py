# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Parse a dotenv file
# Values can either be KEY=VALUE or KEY="VALUE" or KEY='VALUE'
# Returns all env vars as a dict
def parse_dotenv(file_path):
  envVars: dict = {}
  with open(file_path, 'r') as file:
    for line in file:
      line = line.strip()
      if line.startswith('#') or len(line) == 0:
        continue
      if '=' in line:
        key, value = line.split('=', 1)
        value = value.strip('"').strip("'")
        envVars[key] = value
      else:
        print("Warning: Invalid line in {}: {}".format(file_path, line))
        print("Line should be in the format KEY=VALUE or KEY=\"VALUE\" or KEY='VALUE'")
        continue
  return envVars
