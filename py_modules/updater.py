"""Self-update from the fork's GitHub releases."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile

REPO = "JoeysRetroHandhelds/CheatDeck"
API_URL = "https://api.github.com/repos/{}/releases/latest".format(REPO)
ALLOWED_HOSTS = {
    "github.com",
    "api.github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}
USER_AGENT = "CheatDeck-Updater"
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024


def parse_version(value: str) -> tuple[int, ...]:
    match = re.match(r"v?(\d+(?:\.\d+)*)", value.strip())
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def _open(url: str):
    if urllib.parse.urlparse(url).hostname not in ALLOWED_HOSTS:
        raise ValueError("URL not allowed: {}".format(url))
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    response = urllib.request.urlopen(request, timeout=30)
    if urllib.parse.urlparse(response.geturl()).hostname not in ALLOWED_HOSTS:
        raise ValueError("Redirected to disallowed host")
    return response


def pick_assets(release: dict) -> tuple[str, str]:
    """Return (zip_url, sha256_url) from a GitHub release payload."""
    assets = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
    zips = [name for name in assets if name.endswith(".zip")]
    if len(zips) != 1:
        raise ValueError("Release must have exactly one .zip asset")
    checksum = zips[0] + ".sha256"
    if checksum not in assets:
        raise ValueError("Release is missing {}".format(checksum))
    return assets[zips[0]], assets[checksum]


def check(current_version: str) -> dict:
    with _open(API_URL) as response:
        release = json.load(response)
    latest = release.get("tag_name", "")
    return {
        "current": current_version,
        "latest": latest,
        "available": is_newer(latest, current_version),
        "notes": release.get("body") or "",
    }


def _download(url: str, path: str) -> str:
    digest = hashlib.sha256()
    size = 0
    with _open(url) as response, open(path, "wb") as out:
        while chunk := response.read(64 * 1024):
            size += len(chunk)
            if size > MAX_DOWNLOAD_BYTES:
                raise ValueError("Download too large")
            digest.update(chunk)
            out.write(chunk)
    return digest.hexdigest()


def _extract_plugin(zip_path: str, dest: str) -> str:
    """Extract the release zip and return the folder containing plugin.json."""
    root = os.path.realpath(dest)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.namelist():
            target = os.path.realpath(os.path.join(dest, member))
            if target != root and not target.startswith(root + os.sep):
                raise ValueError("Unsafe path in archive: {}".format(member))
        archive.extractall(dest)
    for dirpath, _dirs, files in os.walk(dest):
        if "plugin.json" in files and "main.py" in files:
            return dirpath
    raise ValueError("Release zip does not contain a plugin")


def install(plugin_dir: str, state_dir: str) -> str:
    """Download the latest release and replace plugin_dir, keeping a backup in state_dir.

    state_dir must be outside Decky's plugins folder (or Decky would load the backup as a
    second plugin) and on the same filesystem so the swap is a rename.
    """
    with _open(API_URL) as response:
        release = json.load(response)
    zip_url, sha_url = pick_assets(release)

    os.makedirs(state_dir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="update-", dir=state_dir)
    backup = os.path.join(state_dir, "backup")
    try:
        with _open(sha_url) as response:
            expected = response.read().decode().split()[0].lower()
        actual = _download(zip_url, os.path.join(work, "release.zip"))
        if actual != expected:
            raise ValueError("Checksum mismatch: expected {}, got {}".format(expected, actual))

        new_plugin = _extract_plugin(os.path.join(work, "release.zip"), os.path.join(work, "extract"))

        if os.path.exists(backup):
            shutil.rmtree(backup)
        os.rename(plugin_dir, backup)
        try:
            shutil.move(new_plugin, plugin_dir)
        except Exception:
            os.rename(backup, plugin_dir)
            raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return release.get("tag_name", "")


def rollback(plugin_dir: str, state_dir: str) -> None:
    backup = os.path.join(state_dir, "backup")
    if not os.path.isdir(backup):
        raise ValueError("No backup to restore")
    failed = os.path.join(state_dir, "failed")
    if os.path.exists(failed):
        shutil.rmtree(failed)
    os.rename(plugin_dir, failed)
    os.rename(backup, plugin_dir)


def has_backup(state_dir: str) -> bool:
    return os.path.isdir(os.path.join(state_dir, "backup"))


def restart_loader() -> None:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ""
    subprocess.Popen(["systemctl", "restart", "plugin_loader.service"], env=env)
