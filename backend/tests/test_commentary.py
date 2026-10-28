from matches.engine.commentary import delivery_commentary

BASE = dict(seed=0, batter="R Sharma", bowler="J Bumrah", runs_bat=0, wides=0, noballs=0, byes=0, legbyes=0,
            penalty_runs=0, is_boundary=False, is_penalty_only=False)


def test_four_mentions_zone_only_when_recorded():
    text = delivery_commentary("en", **{**BASE, "runs_bat": 4, "is_boundary": True})
    assert text.startswith("FOUR!") and "cover" not in text
    text = delivery_commentary("en", **{**BASE, "runs_bat": 4, "is_boundary": True, "shot_zone": "cover"})
    assert "through the covers" in text


def test_marathi_and_hindi_templates():
    mr = delivery_commentary("mr", **{**BASE, "runs_bat": 4, "is_boundary": True, "shot_zone": "cover"})
    hi = delivery_commentary("hi", **{**BASE, "runs_bat": 6, "is_boundary": True})
    assert mr.startswith("चौकार!") and "कव्हर्स" in mr
    assert hi.startswith("छक्का!")


def test_wicket_and_extras():
    w = delivery_commentary("en", **{**BASE, "wicket_kind": "caught", "player_out": "R Sharma", "fielder": "V Kohli"})
    assert "WICKET" in w or "OUT" in w
    assert "V Kohli" in w
    nb = delivery_commentary("hi", **{**BASE, "noballs": 1, "next_is_free_hit": True})
    assert "नो-बॉल" in nb and "फ्री हिट" in nb
    wd = delivery_commentary("mr", **{**BASE, "wides": 1})
    assert "वाइड" in wd


def test_unknown_language_falls_back_to_english():
    assert delivery_commentary("fr", **BASE).startswith(("No run", "J Bumrah"))
