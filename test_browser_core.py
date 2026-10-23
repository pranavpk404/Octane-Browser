import tempfile
import unittest
from pathlib import Path

from browser_core import (
    DEFAULT_SEARCH_ENGINE,
    add_page,
    load_page_list,
    load_search_engine,
    normalize_address,
    save_page_list,
    save_search_engine,
)


class BrowserCoreTests(unittest.TestCase):
    def test_urls_default_to_https_and_search_terms_use_the_selected_engine(self):
        self.assertEqual(normalize_address("example.com/docs", "https://www.google.com/"), "https://example.com/docs")
        self.assertEqual(normalize_address("privacy first", "https://www.google.com/"), "https://www.google.com/search?q=privacy+first")

    def test_unsafe_and_malformed_input_is_searched_instead_of_navigated(self):
        self.assertEqual(normalize_address("javascript:alert(1)", "https://duckduckgo.com/"), "https://duckduckgo.com/?q=javascript%3Aalert%281%29")
        self.assertEqual(normalize_address("", "not a supported engine"), DEFAULT_SEARCH_ENGINE)

    def test_search_engine_persistence_is_validated_and_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "search_engine.txt"
            self.assertEqual(save_search_engine(path, "https://www.bing.com/"), "https://www.bing.com/")
            self.assertEqual(load_search_engine(path), "https://www.bing.com/")
            path.write_text("file:///etc/passwd\n", encoding="utf-8")
            self.assertEqual(load_search_engine(path), DEFAULT_SEARCH_ENGINE)

    def test_history_and_bookmarks_are_bounded_deduplicated_and_recover_from_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pages.json"
            entries = add_page([], "https://example.com", "Example", "2026-10-23T00:00:00+00:00", 2)
            entries = add_page(entries, "https://example.com", "Example updated", "2026-10-23T01:00:00+00:00", 2)
            entries = add_page(entries, "https://example.org", "Example Org", "2026-10-23T02:00:00+00:00", 2)
            save_page_list(path, entries, 2)
            self.assertEqual([item["url"] for item in load_page_list(path, 2)], ["https://example.org", "https://example.com"])
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(load_page_list(path, 2), [])


if __name__ == "__main__":
    unittest.main()
