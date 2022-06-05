#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<EOF
${CLI_NAME}-cli v${CLI_VERSION}
Manage your Citadel.

Usage: ${CLI_NAME} <command> [options]

Flags:
    -h, --help                         Show this help message
    -v, --version                      Show version information for this CLI

Commands:
    debug                              View logs for troubleshooting
    restart                            Restart the Citadel service
    reboot                             Reboot the system
    shutdown                           Shutdown the system
    update                             Update Citadel
    backup                             Backup a choice of files and folders
    set <command>                      Configure Citadel
    app <command>                      Install, update or restart apps
    configure <service>                Edit service & app configuration files
EOF
}

edit_file() {
  if [[ $1 = "--priviledged" ]]; then
    echo "Editing this file requires elevated priviledges."

    if ! sudo test -f $2; then
      echo "File not found."
      exit 1
    fi

    if sudo test -w $2; then
      sudo $EDITOR $2
    else
      echo "File not writable."
    fi
  else
    if ! test -f $1; then
      echo "File not found."
      exit 1
    fi

    if test -w $1; then
      $EDITOR $1
    else
      echo "File not writable."
    fi
  fi
}

get_update_channel() {
  update_channel_line=$(cat $CITADEL_ROOT/.env | grep UPDATE_CHANNEL)
  update_channel=(${update_channel_line//=/ })

  if [ -z ${update_channel[1]+x} ]; then
    # fall back to stable
    echo "stable"
  else
    echo ${update_channel[1]}
  fi
}

prompt_apply_config() {
  service=$1
  persisted=$2

  read -p "Do you want to apply the changes now? [y/N] " should_restart
  echo
  if [[ $should_restart =~ [Yy]$ ]]; then
    if $persisted; then
      sudo $CITADEL_ROOT/scripts/configure
    fi

    printf "\nRestarting service \"$service\"...\n"
    docker restart $service
    echo "Done."
  else
    if $persisted; then
      echo "To apply the changes, restart Citadel by running \`$CLI_NAME restart\`."
    else
      echo "To apply the changes, restart service \"$service\" by running \`docker restart $service\`."
    fi
  fi
}
