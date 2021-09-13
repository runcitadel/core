import re
from lib.composegenerator.shared.const import always_allowed_env
from lib.citadelutils import checkArrayContainsAllElements, getEnvVars

def validateEnvByValue(env: list, allowed: list, app_name: str):
    # Combine always_allowed_env with allowed into one list
    # Then check if all elements in env are in the resulting list
    all_allowed = allowed + always_allowed_env
    if(not checkArrayContainsAllElements(env, all_allowed)):
        # This has a weird syntax, and it confuses VSCode, but it works
        validation_regex = r"APP_{}(\S+)".format(
            app_name.upper().replace("-", "_"))
        for key in env:
            # If the key is neither in all_allowed nor is a full match against the validation regex, print a warning and return false
            if(key not in all_allowed and re.fullmatch(validation_regex, key) is None):
                print("Invalid environment variable {} in app {}".format(
                    key, app_name))
                return False
    return True


def validateEnv(app: dict):
    # For every container of the app, check if all env vars in the strings in environment are defined in env
    for container in app['containers']:
        if 'environment' in container:
            if 'environment_allow' in container:
                existingEnv = list(container['environment_allow'].keys())
                del container['environment_allow']
            else:
                existingEnv = []
            # The next step depends on the type of the environment object, which is either a list or dict
            # If it's a list, split every string in it by the first=, then run getEnvVars(envVarValue) on it
            # ON a dict, run getEnvVars(envVarValue) on every value of the environment object
            # Then check if all env vars returned by getEnvVars are defined in env
            if(isinstance(container['environment'], list)):
                raise Exception("List env vars are no longer supported for container {} of app {}".format(
                    container['name'], app['metadata']['name']))
            elif(isinstance(container['environment'], dict)):
                for envVar in container['environment'].values():
                    if(not validateEnvByValue(getEnvVars(envVar), existingEnv, app['metadata']['id'])):
                        raise Exception("Env vars not defined for container {} of app {}".format(
                            container['name'], app['metadata']['name']))
