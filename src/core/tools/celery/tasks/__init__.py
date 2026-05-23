import importlib
import pkgutil

"""
pkgutil.iter_modules(__path__)
the expression above is a list of python modules inside a directory.

importlib.import_module(f"{__package__}.{module.name}")
the expression above imports each module dynamically
for example if the __package__ is core.models
then it runs something like import core.models.users (users is the module.name)
"""
[importlib.import_module(f"{__package__}.{module.name}") for module in pkgutil.iter_modules(__path__)]
