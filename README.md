<!--
SPDX-FileCopyrightText: 2021 Umbrel. https://getumbrel.com

SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-->

[![Discord Server](https://img.shields.io/badge/Community%20Chat-Discord-%235351FB)](https://discord.gg/6U3kM2cjdB)
[![Twitter](https://img.shields.io/twitter/follow/runcitadel?style=social)](https://twitter.com/runcitadel)

# 🏰 Citadel — a personal server for everyone
> ⚠️ Citadel is currently in beta and is not considered secure. Please see [SECURITY.md](SECURITY.md) for more details.

## ⚠️ Outdated information

The information below might be outdated and / or refering to Umbrel. This project is not yet fully off it's Umbrel roots.


## 🚀 Getting started

TBD

## 🛠 Installation

TBD

### Installation Requirements

- 4GB RAM and 600GB+ free space (for mainnet)
- [Docker](https://docs.docker.com/engine/install)
- [Python 3.0+](https://www.python.org/downloads)
- [fswatch](https://emcrisostomo.github.io/fswatch/), [jq](https://stedolan.github.io/jq/), [rsync](https://linuxize.com/post/how-to-use-rsync-for-local-and-remote-data-transfer-and-synchronization/#installing-rsync), [curl](https://curl.haxx.se/docs/install.html) (`sudo apt-get install fswatch jq rsync curl`)

Make sure your User ID is `1000` (verify it by running `id -u`) and ensure that your account is [correctly permissioned to use docker](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user).

### Step 1. Download Citadel

> Run this in an empty directory where you want to install Citadel. If using an external storage such as an SSD or HDD, run this inside an empty directory on that drive.

```bash
curl -L https://github.com/runcitadel/compose-nonfree/archive/v0.4.10.tar.gz | tar -xz --strip-components=1
```

### Step 2. Run Citadel

```bash
# To use Citadel on mainnet, run:
sudo ./scripts/start

# The following environment settings can only be set
# during first run of the start script and will be persisted through
# any updates

# For testnet, run:
sudo NETWORK=testnet ./scripts/start

# For regtest, run:
sudo NETWORK=regtest ./scripts/start

# For Citadel to listen on port 12345 instead of 80, run:
sudo NGINX_PORT=12345 ./scripts/start
```

To stop Citadel, run:

```bash
sudo ./scripts/stop
```

## 🎹 Services orchestrated

TBD

**Architecture**

```
                          + -------------------- +
                          |       dashboard      |
                          + -------------------- +
                                      |
                                      |
                              + ------------- +
                              |     nginx     |
                              + ------------- +
                                      |
                                      |
              + - - - - - - - - - - - + - - - - - - - - - - - +
              |                                               |
              |                                               |
   + ------------------ +                         + --------------------- +
   |       manager      | < - - - jwt auth - - -  |       middleware      |
   + ------------------ +                         + --------------------- +
                                                              |
                                                              |
                                            + - - - - - - - - + - - - - - - - - +
                                            |                                   |
                                            |                                   |
                                    + ------------- +                   + ------------- +
                                    |   bitcoind    | < - - - - - - - - |      lnd      |
                                    + ------------- +                   + ------------- +
```

---

## ⚡️ Don't be too reckless

Citadel is still in beta development and should not be considered secure. [Read our writeup of security tradeoffs](https://github.com/runcitadel/compose-nonfree/blob/master/SECURITY.md) that exist today.

It's recommended that you note down your 24 secret words (seed phrase) with a pen and paper, and secure it safely. If you forget your dashboard's password, or in case something goes wrong with your Citadel, you will need these 24 words to recover your funds in the Bitcoin wallet of your Citadel.

You're also recommended to download a backup of your payment channels regularly as it'll be required to recover your funds in the Lightning wallet of your Citadel in case something goes wrong. You should also always download the latest backup file before installing an update.

## ❤️ Contributing

We welcome and appreciate new contributions.


## 📜 License


### ⚠️ This information is refering Citadel's Umbrel basis, it is migrating off Umbrel to AGPL.


Umbrel is licensed under the PolyForm Noncommercial 1.0.0 license.

[![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-%235351FB)](https://github.com/getumbrel/umbrel/blob/master/LICENSE.md)

