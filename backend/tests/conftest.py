"""
Test configuration and stubs for modules not available in the test environment.

pyzk (the ZKTeco library) and PyQt6 are not installed in CI test environments —
they require hardware/GUI drivers. We stub them here so imports succeed and
tests can mock the actual calls.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Stub the zk (pyzk) module — not available in test/CI environments
zk_mock = MagicMock()
zk_mock.ZK = MagicMock
sys.modules['zk'] = zk_mock
sys.modules['zk.base'] = MagicMock()
sys.modules['zk.exception'] = MagicMock()
