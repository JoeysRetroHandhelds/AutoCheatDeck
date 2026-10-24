import io
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "py_modules"))

import fling  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


class FlingParserTest(unittest.TestCase):
    def test_parse_search(self):
        results = fling.parse_search(read_fixture("fling_search.html"))
        urls = [r["url"] for r in results]
        self.assertIn("https://flingtrainer.com/trainer/elden-ring-nightreign-trainer/", urls)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(r["title"] for r in results))

    def test_parse_trainer_page(self):
        page = fling.parse_trainer_page(read_fixture("fling_trainer.html"))
        self.assertEqual(page["lastUpdated"], "2026.01.02")
        self.assertEqual(page["versions"][0]["title"], "Elden.Ring.v1.02-v1.16.1.Plus.35.Trainer-FLiNG")
        self.assertTrue(page["versions"][0]["url"].startswith("https://flingtrainer.com/downloads/"))

    def test_rejects_foreign_urls(self):
        with self.assertRaises(ValueError):
            fling.list_versions("https://evil.example.com/trainer/x/")
        with self.assertRaises(ValueError):
            fling.list_versions("http://flingtrainer.com/trainer/x/")


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes, url: str):
        super().__init__(data)
        self._url = url

    def geturl(self):
        return self._url


class SafeReplaceTest(unittest.TestCase):
    PAGE = "https://flingtrainer.com/trainer/hades-trainer/"
    URL = "https://flingtrainer.com/downloads/abc"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = os.path.join(self.tmp.name, "trainers", "1")
        os.makedirs(self.target)
        with open(os.path.join(self.target, "Old Trainer.exe"), "wb") as f:
            f.write(b"MZ old")

    def tearDown(self):
        self.tmp.cleanup()

    def download(self, payload: bytes):
        final = "https://flingtrainer.com/wp-content/uploads/New%20Trainer.exe"
        with mock.patch.object(fling, "_get", return_value=FakeResponse(payload, final)):
            return fling.download(self.URL, self.PAGE, self.target)

    def test_replaces_and_cleans_up(self):
        self.download(b"MZ new")
        self.assertEqual(os.listdir(self.target), ["New Trainer.exe"])
        self.assertEqual(os.listdir(os.path.dirname(self.target)), ["1"])

    def test_locked_trainer_is_left_alone(self):
        with mock.patch.object(fling.os, "rename", side_effect=PermissionError("in use")):
            with self.assertRaisesRegex(ValueError, "Close the trainer"):
                self.download(b"MZ new")
        self.assertEqual(os.listdir(self.target), ["Old Trainer.exe"])

    def test_unusable_download_restores_old_trainer(self):
        with self.assertRaises(ValueError):
            self.download(b"<html>not a trainer</html>")
        self.assertEqual(os.listdir(self.target), ["Old Trainer.exe"])
        self.assertEqual(os.listdir(os.path.dirname(self.target)), ["1"])


if __name__ == "__main__":
    unittest.main()
