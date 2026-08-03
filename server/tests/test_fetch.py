"""Pure-reducer tests for fetch — no network."""

from finance_answer_engine.corpus.fetch import govuk_text, strip_html


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


def test_strip_html_drops_related_link_blocks():
    """Navigation chrome does not always live in a <nav>.

    FCA pages carry related-links blocks as plain <div>/<ul> in the body, and a
    tag-only skip let the run of link labels through as if it were prose. The
    engine then answered "how do I protect myself from financial scams?" out of
    a menu — a citable claim made of link text.
    """
    html = """
    <html><body><main>
      <p>Report a scam to us as soon as you can.</p>
      <div class="related-links">
        <ul><li><a href="/a">Mortgage fraud</a></li>
            <li><a href="/b">Protect yourself from scams</a></li>
            <li><a href="/c">How to complain</a></li></ul>
      </div>
      <p>We will not ask for your password.</p>
    </main></body></html>"""
    text = strip_html(html)
    assert "Report a scam to us as soon as you can." in text
    assert "We will not ask for your password." in text
    assert "Protect yourself from scams" not in text
    assert "How to complain" not in text


def test_prose_before_a_chrome_block_is_not_glued_to_what_follows():
    """The buffer is flushed when chrome starts, or two real sentences merge."""
    html = """
    <html><body><main>
      Text before the block
      <div class="related-links"><a href="/x">Some link</a></div>
      <p>A real sentence.</p>
    </main></body></html>"""
    text = strip_html(html)
    assert "Some link" not in text
    assert "Text before the block A real sentence" not in text


def test_strip_html_drops_the_page_title():
    """A <title> is site chrome, not body prose.

    It was being extracted as the first sentence of every FCA page, brand suffix
    and all, then offered as a citable claim. Every Passage already carries the
    real document title separately.
    """
    html = """
    <html><head><title>Protect yourself from scams | FCA</title></head>
    <body><main><p>Criminals may pose at your bank.</p></main></body></html>"""
    text = strip_html(html)
    assert "| FCA" not in text
    assert "Criminals may pose at your bank." in text


def test_a_nested_div_cannot_close_a_skipped_block_early():
    """The skip has to survive nesting, or chrome leaks back in mid-block."""
    html = """
    <html><body><main>
      <div class="related-links">
        <div><span>Buried link label</span></div>
        <div>Another label</div>
      </div>
      <p>Genuine prose here.</p>
    </main></body></html>"""
    text = strip_html(html)
    assert "Buried link label" not in text
    assert "Another label" not in text
    assert "Genuine prose here." in text
