# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import re
import fcntl
import os

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
        print("Error: Invalid line in {}: {}".format(file_path, line))
        print("Line should be in the format KEY=VALUE or KEY=\"VALUE\" or KEY='VALUE'")
        exit(1)
  return envVars
  
class FileLock:
    """Implements a file-based lock using flock(2).
    The lock file is saved in directory dir with name lock_name.
    dir is the current directory by default.
    """

    def __init__(self, lock_name, dir="."):
        self.lock_file = open(os.path.join(dir, lock_name), "w")

    def acquire(self, blocking=True):
        """Acquire the lock.
        If the lock is not already acquired, return None.  If the lock is
        acquired and blocking is True, block until the lock is released.  If
        the lock is acquired and blocking is False, raise an IOError.
        """
        ops = fcntl.LOCK_EX
        if not blocking:
            ops |= fcntl.LOCK_NB
        fcntl.flock(self.lock_file, ops)

    def release(self):
        """Release the lock. Return None even if lock not currently acquired"""
        fcntl.flock(self.lock_file, fcntl.LOCK_UN)
  