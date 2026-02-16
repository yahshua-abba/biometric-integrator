"""
Centralized version management.
Reads version from VERSION file (bundled in production builds) or git tags (development).
"""

import os
import sys
import subprocess


def _get_base_path():
    """Get the base path for the application (handles PyInstaller frozen bundles)."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _read_version_file():
    """Try to read version from VERSION file."""
    version_file = os.path.join(_get_base_path(), 'VERSION')
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            version = f.read().strip()
            if version:
                return version
    return None


def _read_git_tag():
    """Try to read version from the latest git tag (development only)."""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True, text=True, timeout=5,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            tag = result.stdout.strip()
            return tag.lstrip('v')
    except Exception:
        pass
    return None


def get_version():
    """Get the application version. Checks VERSION file first, then git tags."""
    return _read_version_file() or _read_git_tag() or '0.0.0'


APP_VERSION = get_version()
