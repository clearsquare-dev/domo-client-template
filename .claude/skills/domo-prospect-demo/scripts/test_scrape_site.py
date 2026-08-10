import unittest
from unittest.mock import patch

import requests
from bs4 import BeautifulSoup

import scrape_site as ss


SAMPLE_HTML = """
<html>
<head>
  <title>Acme Rocket Co - Fly Higher</title>
  <meta name="description" content="Acme builds rockets for small business.">
  <meta name="theme-color" content="#1B4F72">
  <link rel="icon" href="/favicon.ico">
  <style>
    body { font-family: 'Poppins', sans-serif; }
    .hero { background: #1B4F72; color: #FFFFFF; }
    .cta { background-color: #F39C12; }
  </style>
</head>
<body>
  <img src="/assets/acme-logo.svg" alt="Acme Rocket Co logo" class="site-logo">
  <h1>We build rockets</h1>
  <p>Acme Rocket Co helps small businesses launch payloads into orbit affordably.</p>
</body>
</html>
"""


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.soup = BeautifulSoup(SAMPLE_HTML, "html.parser")

    def test_extract_title_and_description(self):
        title, description = ss.extract_title_and_description(self.soup)
        self.assertEqual(title, "Acme Rocket Co - Fly Higher")
        self.assertEqual(description, "Acme builds rockets for small business.")

    def test_extract_colors_ranks_theme_color_first(self):
        colors, theme_color = ss.extract_colors(self.soup)
        self.assertEqual(theme_color, "#1B4F72")
        self.assertEqual(colors[0], "#1b4f72")
        self.assertIn("#f39c12", colors)

    def test_extract_colors_excludes_neutrals(self):
        colors, _ = ss.extract_colors(self.soup)
        self.assertNotIn("#ffffff", colors)

    def test_extract_colors_includes_extra_css(self):
        soup = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        colors, _ = ss.extract_colors(soup, extra_css=".hero { background: #ABCDEF; }")
        self.assertIn("#abcdef", colors)

    def test_extract_colors_excludes_grayscale_utility_colors(self):
        soup = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        css = ".t{color:#333} .b{border-color:#999} .bg{background:#e6e6e6} .a{background:#3898ec}"
        colors, _ = ss.extract_colors(soup, extra_css=css)
        self.assertNotIn("#333", colors)
        self.assertNotIn("#999", colors)
        self.assertNotIn("#e6e6e6", colors)
        self.assertIn("#3898ec", colors)

    def test_extract_fonts(self):
        fonts = ss.extract_fonts(self.soup)
        self.assertIn("Poppins", fonts)

    def test_extract_fonts_excludes_generic_and_icon_fonts(self):
        soup = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        css = (
            "body{font-family: webflow-icons, sans-serif} "
            "h1{font-family: unset !important} "
            "p{font-family: 'Helvetica Neue', Arial}"
        )
        fonts = ss.extract_fonts(soup, extra_css=css)
        self.assertNotIn("webflow-icons", fonts)
        self.assertNotIn("unset", fonts)
        self.assertIn("Helvetica Neue", fonts)

    def test_extract_logo_resolves_relative_url(self):
        logo = ss.extract_logo(self.soup, "https://acme.example.com/")
        self.assertEqual(logo, "https://acme.example.com/assets/acme-logo.svg")

    def test_extract_logo_falls_back_to_og_image(self):
        html = (
            "<html><head><meta property='og:image' content='/social/share.png'>"
            "</head><body><img src='/banner.png'></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        logo = ss.extract_logo(soup, "https://acme.example.com/")
        self.assertEqual(logo, "https://acme.example.com/social/share.png")

    def test_extract_logo_falls_back_to_favicon(self):
        html = (
            "<html><head><link rel='icon' href='/fav.ico'></head>"
            "<body><img src='/banner.png'></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        logo = ss.extract_logo(soup, "https://acme.example.com/")
        self.assertEqual(logo, "https://acme.example.com/fav.ico")

    def test_extract_body_text_strips_scripts_and_truncates(self):
        html = "<html><body><script>var x=1;</script><p>" + ("hello " * 1000) + "</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = ss.extract_body_text(soup, max_chars=50)
        self.assertNotIn("var x=1", text)
        self.assertLessEqual(len(text), 50)

    def test_extract_stylesheet_urls_resolves_relative(self):
        html = "<html><head><link rel='stylesheet' href='/css/main.css'></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        urls = ss.extract_stylesheet_urls(soup, "https://acme.example.com/")
        self.assertEqual(urls, ["https://acme.example.com/css/main.css"])

    def test_extract_stylesheet_urls_ignores_non_stylesheet_links(self):
        html = (
            "<html><head><link rel='icon' href='/fav.ico'>"
            "<link rel='stylesheet' href='/a.css'></head><body></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        urls = ss.extract_stylesheet_urls(soup, "https://acme.example.com/")
        self.assertEqual(urls, ["https://acme.example.com/a.css"])


class FetchStylesheetsTests(unittest.TestCase):
    @patch("scrape_site.requests.get")
    def test_fetch_linked_stylesheets_concatenates(self, mock_get):
        mock_get.return_value.text = ".btn { color: #123456; }"
        mock_get.return_value.raise_for_status = lambda: None
        css = ss.fetch_linked_stylesheets(["https://acme.example.com/a.css"])
        self.assertIn("#123456", css)

    @patch("scrape_site.requests.get")
    def test_fetch_linked_stylesheets_skips_failures(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("nope")
        css = ss.fetch_linked_stylesheets(["https://acme.example.com/a.css"])
        self.assertEqual(css, "")


class ScrapeIntegrationTests(unittest.TestCase):
    @patch("scrape_site.fetch_html")
    def test_scrape_success(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_HTML
        result = ss.scrape("https://acme.example.com/")
        self.assertTrue(result["scrape_ok"])
        self.assertEqual(result["title"], "Acme Rocket Co - Fly Higher")
        self.assertEqual(result["logo_url"], "https://acme.example.com/assets/acme-logo.svg")

    @patch("scrape_site.fetch_html")
    def test_scrape_handles_fetch_failure(self, mock_fetch):
        mock_fetch.side_effect = requests.ConnectionError("boom")
        result = ss.scrape("https://doesnotexist.example.com/")
        self.assertFalse(result["scrape_ok"])
        self.assertIn("boom", result["error"])

    @patch("scrape_site.fetch_linked_stylesheets")
    @patch("scrape_site.fetch_html")
    def test_scrape_includes_colors_from_linked_stylesheet(self, mock_fetch_html, mock_fetch_css):
        html = (
            "<html><head><title>T</title>"
            "<link rel='stylesheet' href='/main.css'></head><body></body></html>"
        )
        mock_fetch_html.return_value = html
        mock_fetch_css.return_value = ".hero { background: #654321; }"
        result = ss.scrape("https://acme.example.com/")
        self.assertIn("#654321", result["colors"])
        mock_fetch_css.assert_called_once_with(["https://acme.example.com/main.css"])


if __name__ == "__main__":
    unittest.main()
