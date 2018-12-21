import os
import yaml

with open(os.path.join(os.getcwdu(), "constants.yaml"), "r") as f:
    constants = yaml.load(f)

with open(os.path.join(os.path.expanduser("~"), "tokens.yaml"), "r") as g:
    constants.update(yaml.load(g))

