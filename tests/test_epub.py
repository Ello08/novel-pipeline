import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from PIL import Image

from novel_pipeline.epub_builder import build_epub
from novel_pipeline.scraper import audit


def make_chapter(root: Path, number: str, text: str):
    folder = root / "txt" / "example"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{number}.txt").write_text(text, encoding="utf-8")


class EpubTests(unittest.TestCase):
    def test_builds_chapters_and_embeds_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_chapter(root, "0001", "Chapter One\n\nFirst paragraph.\n\nSecond paragraph.")
            make_chapter(root, "0002", "Chapter Two\n\nThird paragraph.")

            image_dir = root / "img" / "example" / "0001"
            image_dir.mkdir(parents=True)
            Image.new("RGB", (800, 600), "navy").save(image_dir / "01.png")
            (image_dir / "_manifest.json").write_text(json.dumps({
                "images": [{"file": "01.png", "after_para": 0, "alt": "Scene"}],
                "errors": [],
            }), encoding="utf-8")

            destination = build_epub(root, "example", "Example", "Author", "en")

            self.assertTrue(destination.is_file())
            with zipfile.ZipFile(destination) as archive:
                self.assertIsNone(archive.testzip())
                names = archive.namelist()
                self.assertIn("EPUB/images/0001_01.png", names)
                chapter = archive.read("EPUB/chapter_0001.xhtml").decode()
                self.assertIn("First paragraph.", chapter)
                self.assertIn("<figure>", chapter)

    def test_audit_accepts_clean_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_chapter(root, "0001", "One\n\nText.")
            make_chapter(root, "0002", "Two\n\nText.")
            self.assertEqual(audit(root, "example", expected=2, min_chars=0), 0)

    def test_audit_reports_missing_number(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_chapter(root, "0001", "One\n\nText.")
            make_chapter(root, "0003", "Three\n\nText.")
            self.assertEqual(audit(root, "example", expected=3, min_chars=0), 1)

    def test_audit_reports_duplicate_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_chapter(root, "0001", "Same\n\nText.")
            make_chapter(root, "0002", "Same\n\nText.")
            self.assertEqual(audit(root, "example", expected=2, min_chars=0), 1)


if __name__ == "__main__":
    unittest.main()
