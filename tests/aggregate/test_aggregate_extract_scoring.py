from podcast_atlas.aggregate.extract import extract_spans


def test_strong_cue_boosts_score_vs_no_cue():
    seg_no = "Die Gründung der CSU 1946 unter amerikanischer Besatzungsmacht."
    seg_yes = "Im Jahr 1946 wurde die CSU unter amerikanischer Besatzungsmacht gegründet."

    a = extract_spans(seg_no, "main")
    b = extract_spans(seg_yes, "main")

    # both should include the year 1946 span
    a_1946 = next(s for s in a if s.source_text == "1946")
    b_1946 = next(s for s in b if s.source_text == "1946")

    assert b_1946.score > a_1946.score


def test_caption_penalty_beats_main_segment():
    caption = "Das Folgenbild zeigt ein Porträt aus dem Jahr 1930."
    main = "Im Jahr 1712 geschah dies und das."

    cap_sp = extract_spans(caption, "caption")
    main_sp = extract_spans(main, "main")

    cap_1930 = next(s for s in cap_sp if s.source_text == "1930")
    main_1712 = next(s for s in main_sp if s.source_text == "1712")

    assert main_1712.score > cap_1930.score
    assert cap_1930.review_flag in ("caption-folgenbild", "caption-portrait-year")


def test_year_range_shorthand_expands_without_future_jump():
    spans = extract_spans("Konflikt 231-36 zwischen den Reichen.", "main")
    rng = next(s for s in spans if s.source_text == "231-36")
    assert rng.start is not None
    assert rng.end is not None
    assert rng.start.year == 231
    assert rng.end.year == 236


def test_year_range_shorthand_works_for_four_digit_prefix():
    spans = extract_spans("Die Epoche 1708-19 war prägend.", "main")
    rng = next(s for s in spans if s.source_text == "1708-19")
    assert rng.start is not None
    assert rng.end is not None
    assert rng.start.year == 1708
    assert rng.end.year == 1719
