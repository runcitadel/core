<!--
SPDX-FileCopyrightText: 2021-2022 Citadel and contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

<p align="center">
  <img height="300" src="https://avatars.githubusercontent.com/u/86734767">
  <h1 align="center">🏰 Citadel Core</h1>
</p>


[![Twitter](https://img.shields.io/twitter/follow/runcitadel?style=flat-square)](https://twitter.com/runcitadel)
![License](https://img.shields.io/github/license/runcitadel/core?style=flat-square)

Citadel Core contains simple, minimalistic host system components for running a Citadel server.
It uses docker and docker-compose to orchestrate containers for the core system and apps.

This repository also contains `karen`, a background daemon responsible for communication between Citadel docker containers and the Citadel Core.

Citadel Core is a fully FLOSS project which replaces the previous `compose` and `compose-nonfree` repositories.
