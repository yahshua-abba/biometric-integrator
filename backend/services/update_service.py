"""
Biometric Integration - Update Service
Checks GitHub Releases for updates and downloads assets
"""

import logging
import platform
import re

import requests

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/repos/ysc-payroll/integrator_sanbeda_taytay/releases/latest"


def parse_version(version_str):
    """Parse a version string like 'v1.2.3' or '1.2.3' into a tuple of ints."""
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", version_str)
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def check_for_updates(current_version):
    """Check GitHub Releases for a newer version.

    Args:
        current_version: Current app version string (e.g. '1.0.0')

    Returns:
        dict with update_available, latest_version, download_url, release_notes, asset_name, asset_size
    """
    try:
        resp = requests.get(GITHUB_API_URL, timeout=15)
        resp.raise_for_status()
        release = resp.json()

        latest_version = release.get("tag_name", "")
        current_tuple = parse_version(current_version)
        latest_tuple = parse_version(latest_version)

        update_available = latest_tuple > current_tuple

        # Find the right asset for this platform
        download_url = None
        asset_name = None
        asset_size = 0
        system = platform.system()

        for asset in release.get("assets", []):
            name = asset.get("name", "")
            if system == "Darwin" and name.endswith(".dmg"):
                download_url = asset["browser_download_url"]
                asset_name = name
                asset_size = asset.get("size", 0)
                break
            elif system == "Windows" and name.endswith(".zip") and "Windows" in name:
                download_url = asset["browser_download_url"]
                asset_name = name
                asset_size = asset.get("size", 0)
                break

        return {
            "update_available": update_available,
            "latest_version": latest_version.lstrip("v"),
            "download_url": download_url,
            "release_notes": release.get("body", ""),
            "asset_name": asset_name,
            "asset_size": asset_size,
        }

    except requests.RequestException as e:
        logger.error(f"Error checking for updates: {e}")
        raise Exception(f"Failed to check for updates: {e}")


GITHUB_ALL_RELEASES_URL = "https://api.github.com/repos/ysc-payroll/integrator_sanbeda_taytay/releases"
MIN_RELEASE_VERSION = (1, 0, 15)


def get_all_releases():
    """Fetch GitHub releases starting from v1.0.15 onwards.

    Returns:
        list of dicts with tag_name, name, body, published_at, html_url
    """
    try:
        resp = requests.get(GITHUB_ALL_RELEASES_URL, timeout=15)
        resp.raise_for_status()
        releases = resp.json()

        result = []
        for release in releases:
            tag = release.get("tag_name", "")
            if parse_version(tag) < MIN_RELEASE_VERSION:
                continue
            result.append({
                "tag_name": tag,
                "name": release.get("name", "") or tag,
                "body": release.get("body", ""),
                "published_at": release.get("published_at", ""),
                "html_url": release.get("html_url", ""),
            })

        return result

    except requests.RequestException as e:
        logger.error(f"Error fetching releases: {e}")
        raise Exception(f"Failed to fetch releases: {e}")


def download_update(download_url, save_path, progress_callback=None):
    """Download an update asset with progress tracking.

    Args:
        download_url: URL of the asset to download
        save_path: Full file path to save the downloaded file
        progress_callback: Optional callable(percent, downloaded_mb, total_mb)

    Returns:
        save_path on success
    """
    try:
        resp = requests.get(download_url, stream=True, timeout=30)
        resp.raise_for_status()

        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 8192

        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback and total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        downloaded_mb = round(downloaded / (1024 * 1024), 1)
                        total_mb = round(total_size / (1024 * 1024), 1)
                        progress_callback(percent, downloaded_mb, total_mb)

        return save_path

    except requests.RequestException as e:
        logger.error(f"Error downloading update: {e}")
        raise Exception(f"Failed to download update: {e}")
