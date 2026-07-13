from podcast_atlas.aggregate.extract import (
    clean_description,
    extract_spans,
    rake_phrases,
    segment_text,
)


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


def test_clean_description_truncates_terminal_metadata_sections() -> None:
    raw = """
    Im Dezember 1881 brennt das Ringtheater in Wien.
    Wir sprechen über die frühe Elektrifizierung und Thomas Edison.

    // Literatur
    - Paul Israel: Edison: A Life of Invention, 1998.
    - Alexander Bartl: Der elektrische Traum, 2023.

    // Erwähnte Folgen
    - GAG458: Wie wir die Nacht zum Tag machten, 2024.
    """.strip()

    cleaned = clean_description(raw)

    assert "1881" in cleaned
    assert "Elektrifizierung" in cleaned
    assert "1998" not in cleaned
    assert "2023" not in cleaned
    assert "2024" not in cleaned


def test_clean_description_drops_standalone_production_credits() -> None:
    raw = """
    Eine Folge über die Revolution von 1918.
    Hostin: Linda Schildbach
    Sprecherin: Conny Wolter
    Redaktion: Stefan Nölke
    Produktion: MDR KULTUR und JUGEND 2025
    Autor und Producer: Thomas Hartmann
    """.strip()

    cleaned = clean_description(raw)

    assert cleaned == "Eine Folge über die Revolution von 1918."


def test_clean_description_truncates_inline_schedule_and_cross_promotion() -> None:
    raw = (
        "Die Kartoffelfäule beginnt 1845 in Irland. Matthias von Hellfeld erzählt. "
        "Hörenswert: Das Jahr ohne Sommer. "
        "Die passende Ausgabe ‘Eine Stunde History’ läuft am 15. September 2025 auf DLFnova."
    )

    cleaned = clean_description(raw)

    assert cleaned == "Die Kartoffelfäule beginnt 1845 in Irland."
    assert "2025" not in cleaned
    assert "Das Jahr ohne Sommer" not in cleaned

    schedule_only = clean_description(
        "Über Kindererziehung. Die passende Ausgabe “Eine Stunde History” läuft am 6. Oktober 2025 auf DLFnova."
    )
    assert schedule_only == "Über Kindererziehung."
    malformed_schedule = clean_description(
        "Im Jahr 1879 eröffnet Tietz sein Warenhaus. Die passende Ausgabe “Eine Stunde History” läuft am19. August 2019 auf DLFnova."
    )
    assert malformed_schedule == "Im Jahr 1879 eröffnet Tietz sein Warenhaus."


def test_clean_description_truncates_inline_affiliate_and_depublication_metadata() -> None:
    assert (
        clean_description(
            "Eine Folge über die Hallstein-Doktrin. *Affiliate-Link: Wer über diesen Link kauft."
        )
        == "Eine Folge über die Hallstein-Doktrin."
    )
    assert (
        clean_description(
            "Folge über Michail Gorbatschow. Ursprünglich wurden die Sendungen bei Deutschlandradio Wissen veröffentlicht."
        )
        == "Folge über Michail Gorbatschow."
    )
    assert clean_description("Eine Folge über die Inquisition. (DLFnova)") == (
        "Eine Folge über die Inquisition."
    )


def test_clean_description_removes_flattened_promotional_sentences() -> None:
    raw = (
        "Die Hanse prägt den Handel im Ostseeraum. "
        "Wir freuen uns, wenn ihr den Podcast bei Apple Podcasts bewertet. "
        "Im 14. Jahrhundert wächst Lübeck zu einem wichtigen Zentrum. "
        "Hosted on Acast. See acast.com/privacy for more information."
    )

    cleaned = clean_description(raw)

    assert "Hanse" in cleaned
    assert "14. Jahrhundert" in cleaned
    assert "Apple Podcasts" not in cleaned
    assert "Acast" not in cleaned


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


def test_segment_text_stops_at_terminal_heading_defensively() -> None:
    pure = """
    Beethoven arbeitet zu Beginn des 19. Jahrhunderts an seiner Eroica.

    Literatur

    Swafford, Jan: Beethoven: Anguish and Triumph, 2014.
    """.strip()

    assert segment_text(pure) == [
        ("main", "Beethoven arbeitet zu Beginn des 19. Jahrhunderts an seiner Eroica.")
    ]


def test_title_span_is_weighted_as_high_signal_evidence() -> None:
    title_span = extract_spans("Das Jahr 536 und die Spätantike Kleine Eiszeit", "title")[0]
    main_span = extract_spans("Das Jahr 536 und die Spätantike Kleine Eiszeit", "main")[0]

    assert title_span.start is not None
    assert title_span.start.year == 536
    assert title_span.score > main_span.score


def test_century_extraction_accepts_german_genitive() -> None:
    spans = extract_spans(
        "Beethoven arbeitet zu Beginn des 19. Jahrhunderts an seiner Eroica.",
        "main",
    )

    assert spans
    assert spans[0].start is not None
    assert spans[0].start.year == 1801
    assert spans[0].end is not None
    assert spans[0].end.year == 1900


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
