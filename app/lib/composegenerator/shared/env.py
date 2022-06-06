# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import re
from typing import Union
from lib.composegenerator.v2.types import App
from lib.composegenerator.shared.const import always_allowed_env
from lib.citadelutils import checkArrayContainsAllElements, getEnvVars

def validateEnvByValue(env: list, allowed: list, app_name: str):
    # Combine always_allowed_env with allowed into one list
    # Then check if all elements in env are in the resulting list
    all_allowed = allowed + always_allowed_env
    if not checkArrayContainsAllElements(env, all_allowed):
        # This has a weird syntax, and it confuses VSCode, but it works
        validation_regex = r"APP_{}(\S+)".format(
            app_name.upper().replace("-", "_"))
        for key in env:
            # If the key is neither in all_allowed nor is a full match against the validation regex, print a warning and return false
            if key not in all_allowed and re.fullmatch(validation_regex, key) is None and not key.startswith("APP_HIDDEN_SERVICE")and not key.startswith("APP_SEED"):
                print("Invalid environment variable {} in app {}".format(
                    key, app_name))
                return False
    return True

def validateEnvStringOrListorDict(env: Union[str, Union[list, dict]], existingEnv: list, app_name: str, container_name: str):
    envList = []
    if isinstance(env, dict):
        envList = env.values()
    elif isinstance(env, list):
        envList = env
    elif isinstance(env, str):
        envList = [env]
    for envVar in envList:
        if not validateEnvByValue(getEnvVars(envVar), existingEnv, app_name):
            raise Exception("Env var {} not defined for container {} of app {}".format(envVar, container_name, app_name))
    

def validateEnv(app: App):
    # For every container of the app, check if all env vars in the strings in environment are defined in env
    for container in app.containers:
        if container is not None:
            if container.environment_allow:
                existingEnv = container.environment_allow
                del container.environment_allow
            else:
                existingEnv = []
            if container.environment:
                validateEnvStringOrListorDict(container.command, existingEnv, app.metadata.id, container.name)
                validateEnvStringOrListorDict(container.entrypoint, existingEnv, app.metadata.id, container.name)
                validateEnvStringOrListorDict(container.environment, existingEnv, app.metadata.id, container.name)
    return app
