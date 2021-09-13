
def permissions():
    return {
        "lnd": {
            "environment_allow": {
                "LND_IP": "${LND_IP}",
                "LND_GRPC_PORT": "${LND_GRPC_PORT}",
                "LND_REST_PORT": "${LND_REST_PORT}",
                "BITCOIN_NETWORK": "${BITCOIN_NETWORK}"
            },
            "volumes": [
                '${LND_DATA_DIR}:/lnd:ro'
            ]
        },
        "bitcoind": {
            "environment_allow": {
                "BITCOIN_IP":                 "${BITCOIN_IP}",
                "BITCOIN_NETWORK":            "${BITCOIN_NETWORK}",
                "BITCOIN_P2P_PORT":           "${BITCOIN_P2P_PORT}",
                "BITCOIN_RPC_PORT":           "${BITCOIN_RPC_PORT}",
                "BITCOIN_RPC_USER":           "${BITCOIN_RPC_USER}",
                "BITCOIN_RPC_PASS":           "${BITCOIN_RPC_PASS}",
                "BITCOIN_RPC_AUTH":           "${BITCOIN_RPC_AUTH}",
                "BITCOIN_ZMQ_RAWBLOCK_PORT":  "${BITCOIN_ZMQ_RAWBLOCK_PORT}",
                "BITCOIN_ZMQ_RAWTX_PORT":     "${BITCOIN_ZMQ_RAWTX_PORT}",
                "BITCOIN_ZMQ_HASHBLOCK_PORT": "${BITCOIN_ZMQ_HASHBLOCK_PORT}",
            },
            "volumes": [
                "${BITCOIN_DATA_DIR}:/bitcoin:ro"
            ]
        },
        "electrum": {
            "environment_allow": {
                "ELECTRUM_IP": "${ELECTRUM_IP}",
                "ELECTRUM_PORT": "${ELECTRUM_PORT}",
            }
        }
    }

# Vars which are always allowed without permissions
always_allowed_env = ["TOR_PROXY_IP", "TOR_PROXY_PORT",
                      "APP_DOMAIN", "APP_HIDDEN_SERVICE", "BITCOIN_NETWORK"]
