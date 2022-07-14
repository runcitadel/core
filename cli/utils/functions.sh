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
    status                             Check the status of all services
    start                              Start the Citadel service
    stop                               Stop the Citadel service safely
    restart                            Restart the Citadel service
    reboot                             Reboot the system
    shutdown                           Shutdown the system
    update                             Update Citadel
    set <command>                      Switch between Bitcoin & Lightning implementations
    app <command>                      Install, update or restart apps
    configure <service>                Edit service & app configuration files
    list                               List all installed services apps
    logs <service>                     Show logs for an app or service
    debug                              View logs for troubleshooting
EOF
}

is_managed_by_systemd() {
  if systemctl --all --type service | grep -q "$SERVICE_NAME"; then
    echo true
  else
    echo false
  fi
}

is_service_active() {
  service_status=$(systemctl is-active $SERVICE_NAME)
  if [[ "$service_status" = "active" ]]; then
    echo true
  else
    echo false
  fi
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
