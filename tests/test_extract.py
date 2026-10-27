import unittest

from novel_pipeline.extract import extract, incomplete_reason


class ExtractTests(unittest.TestCase):
    def test_extracts_title_paragraphs_images_and_next_link(self):
        html = """
        <html><head><title>Story - Chapter 1</title></head><body>
          <h1>Chapter 1</h1>
          <div class="chapter-content">
            <p>First paragraph.</p>
            <p>Line one.<br>Line two.</p>
            <img data-src="/images/pic.jpg" alt="Scene">
          </div>
          <a rel="next" href="/story/chapter-2">Next</a>
        </body></html>
        """
        title, paragraphs, images, next_url = extract(
            html, "https://example.org/story/chapter-1"
        )
        self.assertEqual(title, "Chapter 1")
        self.assertEqual(paragraphs, ["First paragraph.", "Line one.", "Line two."])
        self.assertEqual(images[0]["url"], "https://example.org/images/pic.jpg")
        self.assertEqual(images[0]["after_para"], 2)
        self.assertEqual(next_url, "https://example.org/story/chapter-2")

    def test_skips_data_images(self):
        html = """
        <div class="chapter-content">
          <p>Text long enough to be considered a chapter body.</p>
          <img src="data:image/png;base64,AAAA">
        </div>
        """
        _, _, images, _ = extract(html, "https://example.org/chapter-1")
        self.assertEqual(images, [])

    def test_rejects_next_link_on_another_host(self):
        html = """
        <div class="chapter-content"><p>Some chapter text.</p></div>
        <a rel="next" href="https://other.example/chapter-2">Next</a>
        """
        _, _, _, next_url = extract(html, "https://example.org/chapter-1")
        self.assertIsNone(next_url)

    def test_detects_loading_tail(self):
        self.assertIsNotNone(incomplete_reason(["Some text", "Loading..."]))
        self.assertIsNotNone(incomplete_reason(["Bölüm içeriği yüklenemedi."]))
        self.assertIsNone(incomplete_reason(["A finished chapter."]))


if __name__ == "__main__":
    unittest.main()
