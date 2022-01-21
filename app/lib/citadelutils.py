# SPDX-FileCopyrightText: 2021 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import re

# Helper functions


# Return a list of env vars in a string, supports both $NAME and ${NAME} format for the env var
# This can potentially be used to get around permissions, so this check is critical for security
# Please report any security vulnerabilities you find in this check to aaron.dewes@protonmail.com
def getEnvVars(string: str):
    string = str(string)
    envVars = re.findall(r'\$\{.*?\}', string)
    newEnvVars = re.findall(r"\$(?!{)([A-z1-9]+)", string)
    return [envVar[2:-1] for envVar in envVars] + newEnvVars


# Check if an array only contains values which are also in another array
def checkArrayContainsAllElements(array: list, otherArray: list):
    for element in array:
        if element not in otherArray:
            return False
    return True

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

# Combines an object and a class
# If the key exists in both objects, the value of the second object is used
# If the key does not exist in the first object, the value from the second object is used
# If a key contains a list, the second object's list is appended to the first object's list
# If a key contains another object, these objects are combined
def combineObjectAndClass(theClass, obj: dict):
  for key, value in obj.items():
    if key in theClass.__dict__:
      if isinstance(value, list):
        if isinstance(theClass.__dict__[key], list):
          theClass.__dict__[key].extend(value)
        else:
          theClass.__dict__[key] = [theClass.__dict__[key]] + value
      elif isinstance(value, dict):
        if isinstance(theClass.__dict__[key], dict):
          theClass.__dict__[key].update(value)
        else:
          theClass.__dict__[key] = {theClass.__dict__[key]: value}
      else:
        theClass.__dict__[key] = value
    else:
      theClass.__dict__[key] = value

def is_builtin_type(obj):
  return isinstance(obj, (int, float, str, bool, list, dict))

# Convert a class to a dict
# Also strip any class member which is null or empty
def classToDict(theClass):
  obj: dict = {}
  for key, value in theClass.__dict__.items():
    if value is None or (isinstance(value, list) and len(value) == 0):
      continue
    if isinstance(value, list):
      newList = []
      for element in value:
        if is_builtin_type(element):
          newList.append(element)
        else:
          newList.append(classToDict(element))
        obj[key] = newList
    elif isinstance(value, dict):
      newDict = {}
      for subkey, subvalue in value.items():
        if is_builtin_type(subvalue):
          newDict[subkey] = subvalue
        else:
          newDict[subkey] = classToDict(subvalue)
      obj[key] = newDict
    elif is_builtin_type(value):
      obj[key] = value
    else:
      #print(value)
      obj[key] = classToDict(value)
  return obj
  
