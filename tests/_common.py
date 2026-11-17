"""Shared setup for the tests: locate the starter kit and load an agent file."""
import importlib.util
import os
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
KIT = os.environ.get("CHESS_KIT", os.path.dirname(REPO))
DEFAULT_AGENT = os.path.join(REPO, "kestrel_v3.py")

if KIT not in sys.path:
    sys.path.insert(0, KIT)
try:
    import chess_tournament_api  # noqa: F401
except ImportError:
    sys.exit(f"Cannot find the starter kit at {KIT}. Put this folder inside the starter-kit root "
             "or set CHESS_KIT to the starter-kit folder.")


def load_agent(path=None):
    """Import an agent file as a module (the file under test)."""
    path = os.path.abspath(path or DEFAULT_AGENT)
    spec = importlib.util.spec_from_file_location("agent_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def agent_path_from_argv(position=1):
    return sys.argv[position] if len(sys.argv) > position and sys.argv[position].endswith(".py") else None
