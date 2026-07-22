#!/usr/bin/env python3
"""E5 test script — deliberate symptom/root-cause confusion.

When run, this script raises ImportError, but the real problem is NOT
a missing module — it's a path configuration issue. The module exists.
"""

# The real issue: this relative import assumes cwd is the scripts/ directory
# but when run from project root, Python can't find the lib module.
# Surface symptom = ImportError, real root cause = PYTHONPATH/cwd mismatch.
from lib.ga_observability_io import load_observability_data

if __name__ == "__main__":
    print(load_observability_data())
