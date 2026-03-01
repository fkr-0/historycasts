from podcast_atlas.aggregate.gazetteer import Gazetteer, GazetteerEntry


def test_gazetteer_lookup_alias():
    g = Gazetteer(
        [
            GazetteerEntry("Deutschland", "country", 51.0, 10.0, 400.0, ("Germany", "DE")),
        ]
    )
    assert g.lookup("Germany").canonical_name == "Deutschland"
    assert g.lookup("DE").canonical_name == "Deutschland"
