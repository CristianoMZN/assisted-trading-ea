import unittest

from backend.news import RSSNewsAdapter


RSS = b"""<?xml version='1.0'?>
<rss version='2.0'><channel>
  <item><title>Ibovespa and B3 open higher</title><description>Brazilian stocks advance.</description><pubDate>Wed, 25 Nov 2026 14:00:00 GMT</pubDate></item>
  <item><title>Movie awards announced</title><description>Arts coverage.</description><pubDate>Wed, 25 Nov 2026 13:00:00 GMT</pubDate></item>
</channel></rss>"""


class NewsAdapterTests(unittest.TestCase):
    def test_relevant_news_has_source_and_publication_time(self):
        adapter = RSSNewsAdapter(
            ["https://news.example.test/rss"],
            transport=lambda _url, _timeout: RSS,
        )
        result = adapter.collect("WIN")[0]
        self.assertEqual(result.status, "available")
        self.assertEqual(result.source, "news.example.test")
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].published_at, "2026-11-25T14:00:00Z")

    def test_no_relevant_news_is_distinct_from_failure(self):
        adapter = RSSNewsAdapter(
            ["https://news.example.test/rss"],
            transport=lambda _url, _timeout: b"<rss><channel><item><title>Arts</title></item></channel></rss>",
        )
        self.assertEqual(adapter.collect("WDO")[0].status, "empty")

    def test_unavailable_source_has_explicit_failure_state(self):
        def fail(_url, _timeout):
            raise TimeoutError("timeout")

        result = RSSNewsAdapter(["https://news.example.test/rss"], transport=fail).collect("WDO")[0]
        self.assertEqual(result.status, "unavailable")
        self.assertIn("indisponível", result.summary)

    def test_missing_configuration_is_explicit(self):
        result = RSSNewsAdapter([]).collect("WIN")[0]
        self.assertEqual(result.status, "not_configured")
        self.assertEqual(result.source, "configuration")


if __name__ == "__main__":
    unittest.main()
