# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import subprocess

scriptDir = os.path.dirname(os.path.realpath(__file__))
nodeRoot = os.path.join(scriptDir, "..", "..")

def deriveEntropy(identifier: str):
    seedFile = os.path.join(nodeRoot, "db", "citadel-seed", "seed")
    alternativeSeedFile = os.path.join(nodeRoot, "..", "db", "citadel-seed", "seed")
    if not os.path.isfile(seedFile):
        if os.path.isfile(alternativeSeedFile):
            seedFile = alternativeSeedFile
        else:
            raise Exception("No seed file found")
    with open(seedFile, "r") as f:
        node_seed = f.read().strip()
    entropy = subprocess.check_output(
        'printf "%s" "{}" | openssl dgst -sha256 -binary -hmac "{}" | xxd -p | tr --delete "\n"'.format(identifier, node_seed), shell=True)
    return entropy.decode("utf-8")
