import importlib
import os
import types

import pytest


def import_or_skip(module: str) -> types.ModuleType:
    return importlib.import_module(module) if os.environ.get("REQUIRE_INTEGRATIONS") else pytest.importorskip(module)
