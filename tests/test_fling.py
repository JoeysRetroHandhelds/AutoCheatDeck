import os
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
