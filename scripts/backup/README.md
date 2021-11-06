<!--
SPDX-FileCopyrightText: 2020 Umbrel. https://getumbrel.com

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Automatic Encrypted Backups

The backups are encrypted client side before being uploaded over Tor and are padded with random data. Backups are made immediately as soon as the channel state changes. However, Citadel also makes decoy backups at random intervals to prevent timing-analysis attacks.

These features combined ensure that the backup server doesn't learn any sensitive information about the user's Citadel.

- The IP address of user is hidden due to Tor.
- User's channel data are encrypted client side with a key only known to the Citadel device.
- Random interval decoy backups ensure the server can't correlate backup activity with channel state changes on the Lightning network and correlate a backup ID with a channel pubkey.
- Random padding obscures if the backup size has increased/decreased or remains unchanged due to it being a decoy.

Due to the key/id being deterministically derived from the Citadel seed, all that's needed to fully recover an Citadel is the mnemonic seed phrase. Upon recovery the device can automatically regenerate the same backup id/encryption key, request the latest backup from the backup server, decrypt it, and restore the user's settings and Lightning network channel data.

There is currently no way to disable backups or recover from them in the dashboard yet. Both of these features will be introduced in the coming updates.
