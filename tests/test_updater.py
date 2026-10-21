import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "py_modules"))

import updater  # noqa: E402

ZIP_URL = "https://github.com/x/releases/download/v2.1.0/CheatDeck.zip"
SHA_URL = ZIP_URL + ".sha256"


def make_release_zip(version: str, extra: dict | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CheatDeck/plugin.json", "{}")
        archive.writestr("CheatDeck/main.py", "# " + version)
        for name, data in (extra or {}).items():
            archive.writestr(name, data)
    return buffer.getvalue()


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes, url: str):
        super().__init__(data)
        self._url = url

    def geturl(self):
        return self._url


def fake_open(payload: bytes, checksum: str):
    release = {
        "tag_name": "v2.1.0",
        "assets": [
            {"name": "CheatDeck.zip", "browser_download_url": ZIP_URL},
            {"name": "CheatDeck.zip.sha256", "browser_download_url": SHA_URL},
        ],
    }
    responses = {
        updater.API_URL: json.dumps(release).encode(),
        ZIP_URL: payload,
        SHA_URL: (checksum + "  CheatDeck.zip\n").encode(),
    }
    return lambda url: FakeResponse(responses[url], url)


class VersionTest(unittest.TestCase):
    def test_is_newer(self):
        self.assertTrue(updater.is_newer("v2.1.0", "2.0.0"))
        self.assertTrue(updater.is_newer("v2.0.10", "2.0.9"))
        self.assertFalse(updater.is_newer("v2.0.0", "2.0.0"))
        self.assertFalse(updater.is_newer("v1.9.9", "2.0.0"))
        self.assertFalse(updater.is_newer("garbage", "2.0.0"))

    def test_pick_assets_requires_checksum(self):
        with self.assertRaises(ValueError):
            updater.pick_assets({"assets": [{"name": "CheatDeck.zip", "browser_download_url": ZIP_URL}]})

    def test_rejects_foreign_hosts(self):
        with self.assertRaises(ValueError):
            updater._open("https://evil.example.com/CheatDeck.zip")


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin_dir = os.path.join(self.tmp.name, "plugins", "CheatDeck")
        self.state_dir = os.path.join(self.tmp.name, "data", "CheatDeck", "update")
        os.makedirs(self.plugin_dir)
        with open(os.path.join(self.plugin_dir, "main.py"), "w") as f:
            f.write("# old")

    def tearDown(self):
        self.tmp.cleanup()

    def read_main(self) -> str:
        with open(os.path.join(self.plugin_dir, "main.py")) as f:
            return f.read()

    def test_install_and_rollback(self):
        payload = make_release_zip("v2.1.0")
        with mock.patch.object(updater, "_open", fake_open(payload, hashlib.sha256(payload).hexdigest())):
            self.assertEqual(updater.install(self.plugin_dir, self.state_dir), "v2.1.0")
        self.assertEqual(self.read_main(), "# v2.1.0")
        self.assertTrue(updater.has_backup(self.state_dir))
        self.assertEqual(os.listdir(os.path.dirname(self.plugin_dir)), ["CheatDeck"])

        updater.rollback(self.plugin_dir, self.state_dir)
        self.assertEqual(self.read_main(), "# old")

    def test_checksum_mismatch_leaves_plugin_untouched(self):
        payload = make_release_zip("v2.1.0")
        with mock.patch.object(updater, "_open", fake_open(payload, "0" * 64)):
            with self.assertRaises(ValueError):
                updater.install(self.plugin_dir, self.state_dir)
        self.assertEqual(self.read_main(), "# old")

    def test_unsafe_zip_rejected(self):
        payload = make_release_zip("v2.1.0", {"../../escape.txt": "x"})
        with mock.patch.object(updater, "_open", fake_open(payload, hashlib.sha256(payload).hexdigest())):
            with self.assertRaises(ValueError):
                updater.install(self.plugin_dir, self.state_dir)
        self.assertEqual(self.read_main(), "# old")


if __name__ == "__main__":
    unittest.main()
