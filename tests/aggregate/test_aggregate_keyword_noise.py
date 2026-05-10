from podcast_atlas.aggregate.extract import clean_description, rake_phrases, segment_text


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


def test_segment_text_drops_recurring_ad_and_footer_segments() -> None:
    pure = """
    Eine Folge über Kleopatra und die römische Republik.

    Aus unserer Werbung

    Wir haben auch ein Buch geschrieben: Wer es erwerben will, es ist überall im Handel, aber auch direkt über den Verlag zu erwerben: https://www.piper.de/buecher/geschichten-aus-der-geschichte-isbn-978-3-492-06363-0

    Literatur

    Wir sind jetzt auch bei CampfireFM! Wer direkt in Folgen kommentieren will, Zusatzmaterial und Blicke hinter die Kulissen sehen will: einfach die App installieren und unserer Community beitreten:

    Geschichten aus der Geschichte jetzt auch als Brettspiel! Gibt es dort, wo es auch Becher, T-Shirts oder Hoodies zu kaufen gibt: https://geschichte.shop
    """.strip()

    segments = [text for _, text in segment_text(pure)]

    assert segments == ["Eine Folge über Kleopatra und die römische Republik."]


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


def test_rake_phrases_filters_footer_source_boilerplate() -> None:
    text = (
        "Wir sprechen über die Schlacht bei Poltawa und den Großen Nordischen Krieg. "
        "Wir freuen uns auch immer, wenn ihr uns empfehlen, bewerten aber auch von uns erzählt. "
        "Instagram @wasbishergeschah.podcast Quellen The Great Northern War. "
        "Thomas Asbridge Hosted on Acast See acast.com/privacy for more information. "
        "Große CH Beck Hosted source footer. "
        "Du hast Feedback oder einen Themenvorschlag?"
    )

    phrases = rake_phrases(text, max_phrases=80)
    phrase_texts = [p for p, _ in phrases]

    assert any("schlacht" in p or "poltawa" in p for p in phrase_texts)
    assert all("immer dies möglich" not in p for p in phrase_texts)
    assert all("uns empfehlen" not in p for p in phrase_texts)
    assert all("uns erzählt" not in p for p in phrase_texts)
    assert all("instagram" not in p for p in phrase_texts)
    assert all("quellen" not in p for p in phrase_texts)
    assert all("hosted" not in p for p in phrase_texts)
    assert all("acast" not in p for p in phrase_texts)
    assert all("privacy" not in p for p in phrase_texts)
    assert all("feedback" not in p for p in phrase_texts)
    assert all("themenvorschlag" not in p for p in phrase_texts)
