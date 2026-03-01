from podcast_atlas.extract import (
    extract_links,
    extract_persons,
    extract_time_mentions,
    pick_primary_time,
)


def test_extract_time_mentions_bc_year():
    txt = "Attentat 44 v. Chr. in Rom"
    mentions = extract_time_mentions(txt)
    years = [m.year for m in mentions if m.kind == "year"]
    assert -44 in years

    primary = pick_primary_time(mentions)
    assert primary.kind == "point"
    assert primary.year == -44


def test_extract_links_basic():
    txt = "Mehr: https://example.com/a?b=1 und auch http://example.org/x)"
    links = extract_links(txt)
    assert "https://example.com/a?b=1" in links
    assert "http://example.org/x" in links


def test_extract_persons_supports_particles():
    txt = "Otto von Bismarck trifft Helmut Kohl"
    persons = extract_persons(txt)
    assert "Otto von Bismarck" in persons
    assert "Helmut Kohl" in persons
