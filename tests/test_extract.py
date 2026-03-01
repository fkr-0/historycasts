from podcast_atlas.extract import (
    classify_incident_type,
    extract_locations,
    extract_persons,
    extract_time_mentions,
    pick_primary_location,
    pick_primary_time,
)
from podcast_atlas.gazetteer import Gazetteer


def test_extract_time_year_and_range():
    txt = "Verdun 1916: Kontext 1914-1918"
    mentions = extract_time_mentions(txt)
    years = {m.year for m in mentions if m.kind == "year"}
    assert 1916 in years

    ranges = [m for m in mentions if m.kind == "range_year"]
    assert ranges
    r = ranges[0]
    assert r.start_year == 1914
    assert r.end_year == 1918


def test_pick_primary_time_prefers_specific_year():
    txt = "Kontext 1914-1918, aber Schwerpunkt 1916"
    primary = pick_primary_time(extract_time_mentions(txt))
    assert primary.kind == "point"
    assert primary.year == 1916


def test_extract_locations_from_gazetteer(tmp_path):
    gaz = Gazetteer.from_csv_path("data/gazetteer.csv")
    txt = "Ort: Berlin und später Paris"
    locs = extract_locations(txt, gaz)
    names = {l.name for l in locs}
    assert "Berlin" in names
    assert "Paris" in names


def test_pick_primary_location_first_mention():
    gaz = Gazetteer.from_csv_path("data/gazetteer.csv")
    txt = "Paris, dann Berlin"
    primary = pick_primary_location(extract_locations(txt, gaz), text=txt)
    assert primary.name == "Paris"


def test_extract_persons_basic_heuristic_for_titlecase_sequences():
    txt = "Personen: Julius Caesar, Marcus Junius Brutus und Helmut Kohl."
    persons = extract_persons(txt)
    assert "Julius Caesar" in persons
    assert "Marcus Junius Brutus" in persons
    assert "Helmut Kohl" in persons


def test_incident_type_classification():
    assert classify_incident_type("Schlacht um Verdun 1916") == "battle"
    assert classify_incident_type("Sturmflut in Hamburg 1962") == "disaster"
    assert classify_incident_type("Französische Revolution 1789") == "revolution"
    assert classify_incident_type("Konflikt um die Westsahara") == "conflict"
