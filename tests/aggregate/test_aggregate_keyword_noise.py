from podcast_atlas.aggregate.extract import clean_description, rake_phrases


def test_clean_description_drops_cta_lines() -> None:
    raw = """
    Wir sprechen über die Französische Revolution.
    Wir freuen uns, wenn ihr den Podcast bei Apple Podcasts rezensiert oder bewertet.
    Für alle jene gibt's die Podcastplattform Panoptikum, auch dort könnt ihr euer ganz eigenes Podcasthörer:innenprofil erstellen.
    """.strip()

    cleaned = clean_description(raw)

    assert "Französische Revolution" in cleaned
    assert "Apple Podcasts" not in cleaned
    assert "Panoptikum" not in cleaned
    assert "Podcasthörer" not in cleaned


def test_rake_phrases_filters_url_and_cta_noise() -> None:
    text = (
        "Wir sprechen über die Französische Revolution und den Wiener Kongress. "
        "Mehr auf https://www.example.com/privacy. "
        "Wir freuen uns wenn ihr Apple Podcasts rezensiert."
    )

    phrases = rake_phrases(text, max_phrases=50)
    phrase_texts = [p for p, _ in phrases]

    assert any("französische revolution" in p for p in phrase_texts)
    assert all("http" not in p for p in phrase_texts)
    assert all("www" not in p for p in phrase_texts)
    assert all("apple podcasts" not in p for p in phrase_texts)
    assert all("freuen uns wenn" not in p for p in phrase_texts)
