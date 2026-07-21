"""Pure-reducer tests for fetch — no network."""

from pistis.corpus.fetch import govuk_text, strip_html


def test_strip_html_scopes_to_main():
    html = """
    <html><body>
      <nav><a href="/">Cookie banner and menu junk</a></nav>
      <main><p>The annual allowance is £20,000.</p>
      <script>track()</script>
      <h2>Types of ISA</h2><ul><li>Cash ISA</li></ul></main>
      <footer>Footer junk</footer>
    </body></html>"""
    text = strip_html(html)
    assert "£20,000" in text
    assert "Cash ISA." in text  # heading/list items get terminal punctuation
    assert "junk" not in text
    assert "track()" not in text


def test_strip_html_without_main_takes_body():
    assert strip_html("<p>One rule.</p><p>Two rule.</p>") == "One rule. Two rule."


def test_govuk_text_plain_body():
    payload = {
        "details": {"body": "<p>You pay SDLT over the threshold.</p>"},
        "public_updated_at": "2026-04-06T09:30:00Z",
    }
    text, updated = govuk_text(payload)
    assert text == "You pay SDLT over the threshold."
    assert updated == "2026-04-06"


def test_govuk_text_guide_parts_and_renditions():
    payload = {
        "details": {
            "parts": [
                {
                    "title": "Overview",
                    "body": [
                        {"content_type": "text/govspeak", "content": "raw"},
                        {"content_type": "text/html", "content": "<p>Save up to £20,000.</p>"},
                    ],
                },
                {"title": "Lifetime ISA", "body": "<p>Bonus is 25%.</p>"},
            ]
        }
    }
    text, updated = govuk_text(payload)
    assert "Overview." in text
    assert "Save up to £20,000." in text
    assert "Bonus is 25%." in text
    assert "raw" not in text
    assert updated is None
