import os
import sys
import pkgutil
import importlib

# Initialize the mappings
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Get the current package path
package_path = os.path.dirname(__file__)
package_name = os.path.basename(package_path)

# Add the package path to sys.path if not already present
if package_path not in sys.path:
    sys.path.append(package_path)

# Iterate over all modules in the current package
for module_info in pkgutil.iter_modules([package_path]):
    module_name = module_info.name

    # Skip __init__ module and any non-Python files
    if module_name == '__init__':
        continue

    try:
        # Import the module
        module = importlib.import_module(f'.{module_name}', package_name)

        # Collect NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS if they exist
        if hasattr(module, 'NODE_CLASS_MAPPINGS'):
            NODE_CLASS_MAPPINGS.update(module.NODE_CLASS_MAPPINGS)
        if hasattr(module, 'NODE_DISPLAY_NAME_MAPPINGS'):
            NODE_DISPLAY_NAME_MAPPINGS.update(module.NODE_DISPLAY_NAME_MAPPINGS)
    except Exception as e:
        print(f"Failed to import module {module_name}: {e}")

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

print("RK Tools V0.2 Loaded!")