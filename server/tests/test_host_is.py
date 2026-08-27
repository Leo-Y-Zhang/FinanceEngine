"""The shared host check the URL assertions in the suite are built on.

Those assertions used to read `"moneyhelper.org.uk" in url`. A substring is
satisfied by a look-alike host, so the checks would have passed on a routing
link or manifest locator pointing somewhere else entirely — the one thing they
exist to catch. This pins the distinction so it cannot quietly regress.
"""

from conftest import host_is


def test_exact_host_matches():
    assert host_is("https://register.fca.org.uk/", "register.fca.org.uk")
    assert host_is("https://www.moneyhelper.org.uk/en", "www.moneyhelper.org.uk")


def test_subdomain_matches_its_parent_domain():
    assert host_is("https://www.moneyhelper.org.uk/en", "moneyhelper.org.uk")


def test_lookalike_host_does_not_match():
    # Every one of these contains the domain as a substring.
    assert not host_is("https://moneyhelper.org.uk.example.com/", "moneyhelper.org.uk")
    assert not host_is("https://notmoneyhelper.org.uk/", "moneyhelper.org.uk")
    assert not host_is("https://example.com/moneyhelper.org.uk", "moneyhelper.org.uk")


def test_path_only_locator_has_no_host():
    # GOV.UK manifest entries store a bare path, not an absolute URL.
    assert not host_is("/income-tax-rates", "moneyhelper.org.uk")
