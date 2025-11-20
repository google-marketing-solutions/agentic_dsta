# This file marks the 'src/agentic_dsta' directory as a Python package.
# Its presence allows you to import modules from within this directory.

# For example, if you have src/agentic_dsta/my_module.py, you can import it
# in other parts of the project (like main.py or tests) using:
# from src.agentic_dsta import my_module

# --- Optional Usage ---
# While often kept empty, especially in initial stages, this file can also
# be used to:

# 1. Define package-level variables:
#    Example:
#      __version__ = "0.1.0"

# 2. Make a cleaner public API for the package:
#    You can selectively import classes, functions, or submodules from
#    within the package to make them accessible directly from the package
#    namespace.
#    Example (if you had src/agentic_dsta/core.py with AgentClass):
#      from .core import AgentClass
#
#    This would allow users to import like this:
#      from src.agentic_dsta import AgentClass
#    Instead of:
#      from src.agentic_dsta.core import AgentClass
#
#    Be mindful with this approach to avoid overly long import times or
#    circular dependencies, especially as the package grows.

# 3. Package-level initialization code:
#    Rarely needed, but sometimes used for setup tasks that need to run
#    when the package is imported.
