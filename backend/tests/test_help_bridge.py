import json
import sys
import types
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock
import pytest
from tests.test_retry_bridge import bridge_class

@pytest.fixture
def desktop(monkeypatch, bridge_class):
    clipboard = Mock()
    opener = Mock(return_value=True)
    monkeypatch.setattr(sys.modules['PyQt6.QtCore'], 'QUrl', lambda url: url, raising=False)
    monkeypatch.setitem(sys.modules, 'PyQt6.QtGui', types.SimpleNamespace(QDesktopServices=types.SimpleNamespace(openUrl=opener)))
    monkeypatch.setitem(sys.modules, 'PyQt6.QtWidgets', types.SimpleNamespace(QApplication=types.SimpleNamespace(clipboard=lambda: clipboard)))
    db = Mock()
    return bridge_class(db, None, None), clipboard, opener, db

def test_chatgpt_handoff_preserves_full_guide_and_only_opens_chatgpt(desktop):
    bridge, clipboard, opener, db = desktop
    guide = 'Guide: IN & OUT? # Review\nEmployee grouping — 32 logs / 64 uploads\n' * 150
    result = json.loads(bridge.openChatGPTGuide(guide))
    assert result['success']
    url = urlparse(opener.call_args.args[0])
    assert url.scheme == 'https' and url.netloc == 'chatgpt.com' and url.path == '/'
    assert parse_qs(url.query)['q'] == [guide]
    clipboard.setText.assert_called_once_with(guide)
    assert not db.mock_calls

def test_browser_failure_is_not_reported_as_success(desktop):
    bridge, clipboard, opener, _ = desktop
    opener.return_value = False
    assert not json.loads(bridge.openChatGPTGuide('Guide'))['success']
    clipboard.setText.assert_called_once_with('Guide')

@pytest.mark.parametrize('guide', ['', '   ', 'x' * 30001])
def test_invalid_guide_does_not_open_browser_or_change_clipboard(desktop, guide):
    bridge, clipboard, opener, _ = desktop
    assert not json.loads(bridge.openChatGPTGuide(guide))['success']
    assert not json.loads(bridge.copyHelpGuide(guide))['success']
    opener.assert_not_called()
    clipboard.setText.assert_not_called()

def test_clipboard_failure_still_allows_browser_prefill(desktop):
    bridge, clipboard, opener, _ = desktop
    clipboard.setText.side_effect = RuntimeError('Clipboard unavailable')
    result = json.loads(bridge.openChatGPTGuide('Guide'))
    assert result['success']
    assert 'copy is also' not in result['message']
    opener.assert_called_once()
