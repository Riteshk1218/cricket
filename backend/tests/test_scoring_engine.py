import uuid

import pytest

from core.exceptions import ScoringConflict, ScoringError
from matches.engine import service
from matches.models import Delivery, Match, MatchResult, ScoringCorrection

from .conftest import ball, innings, ready_match

pytestmark = pytest.mark.django_db


def state_of(match):
    return service.replay(innings(match))


def bowl_over(scorer, match, runs=(0, 0, 0, 0, 0, 0)):
    for r in runs:
        ball(scorer, match, runs_bat=r)


def test_legal_deliveries_and_run_rate(scorer):
    match, pa, pb = ready_match(scorer)
    ball(scorer, match, runs_bat=1)
    ball(scorer, match, runs_bat=4)
    ball(scorer, match, runs_bat=0)
    st = state_of(match)
    assert st.total == 5 and st.legal_balls == 3 and st.wickets == 0
    assert st.batters[pa[0].pk].runs == 1 and st.batters[pa[0].pk].balls == 1
    assert st.batters[pa[1].pk].runs == 4 and st.batters[pa[1].pk].fours == 1
    assert st.run_rate == 10.0
    inn = innings(match)
    # After a single the batters crossed; a boundary does not change ends.
    assert inn.striker_id == pa[1].pk


def test_striker_rotation_and_end_of_over(scorer):
    match, pa, pb = ready_match(scorer)
    bowl_over(scorer, match, (1, 0, 0, 0, 0, 0))
    inn = innings(match)
    # 1 run: strike changes to pa[1]; end of over: strike swaps back to pa[0].
    assert inn.striker_id == pa[0].pk and inn.non_striker_id == pa[1].pk
    assert inn.bowler_id is None  # new bowler needed
    with pytest.raises(ScoringError) as exc:
        ball(scorer, match, runs_bat=0)
    assert exc.value.code == "need_bowler"


def test_bowler_cannot_bowl_consecutive_overs(scorer):
    match, pa, pb = ready_match(scorer)
    bowl_over(scorer, match)
    with pytest.raises(ScoringError) as exc:
        service.set_bowler(scorer, match.pk, pb[-1].pk)
    assert exc.value.code == "consecutive_overs"
    service.set_bowler(scorer, match.pk, pb[-2].pk)
    ball(scorer, match, runs_bat=2)
    assert state_of(match).bowlers[pb[-1].pk].maidens == 1


def test_bowling_limit(scorer):
    match, pa, pb = ready_match(scorer, overs=4)  # custom 4 overs -> max 1 over per bowler
    assert match.rules["max_overs_per_bowler"] == 1
    bowl_over(scorer, match)
    service.set_bowler(scorer, match.pk, pb[-2].pk)
    bowl_over(scorer, match)
    with pytest.raises(ScoringError) as exc:
        service.set_bowler(scorer, match.pk, pb[-1].pk)
    assert exc.value.code == "bowler_limit"


def test_wides_and_noballs_are_not_legal(scorer):
    match, pa, pb = ready_match(scorer)
    ball(scorer, match, extra_type="wide")
    ball(scorer, match, extra_type="wide", extra_runs=4, boundary=True)
    ball(scorer, match, extra_type="noball", runs_bat=2)
    st = state_of(match)
    assert st.legal_balls == 0
    assert st.total == 1 + 5 + 3
    assert st.wides == 6 and st.noballs == 1 and st.extras == 7
    bowler = st.bowlers[pb[-1].pk]
    assert bowler.runs == 9 and bowler.balls == 0 and bowler.wides == 2 and bowler.noballs == 1
    # No-ball counts as a ball faced; wides do not.
    assert st.batters[pa[0].pk].balls == 1 and st.batters[pa[0].pk].runs == 2


def test_free_hit_after_noball(scorer):
    match, pa, pb = ready_match(scorer)
    ball(scorer, match, extra_type="noball")
    st = state_of(match)
    assert st.free_hit_next
    with pytest.raises(ScoringError) as exc:
        ball(scorer, match, runs_bat=0, wicket={"kind": "bowled"})
    assert exc.value.code == "free_hit"
    # Wide on a free hit keeps the free hit.
    ball(scorer, match, extra_type="wide")
    assert state_of(match).free_hit_next
    d, _, _ = ball(scorer, match, runs_bat=6)
    assert d.is_free_hit
    assert not state_of(match).free_hit_next


def test_byes_legbyes_and_penalty(scorer):
    match, pa, pb = ready_match(scorer)
    ball(scorer, match, extra_type="bye", extra_runs=2)
    ball(scorer, match, extra_type="legbye", extra_runs=1)
    ball(scorer, match, extra_type="penalty", penalty_runs=5)
    st = state_of(match)
    assert st.total == 8 and st.byes == 2 and st.legbyes == 1 and st.penalty == 5
    assert st.legal_balls == 2
    assert st.bowlers[pb[-1].pk].runs == 0
    # 2 byes (no change of ends) then 1 leg bye: pa0 faced both balls but scored nothing.
    assert st.batters[pa[0].pk].balls == 2 and st.batters[pa[0].pk].runs == 0


def test_invalid_inputs_rejected(scorer):
    match, pa, pb = ready_match(scorer)
    with pytest.raises(ScoringError):
        ball(scorer, match, extra_type="wide", runs_bat=1)
    with pytest.raises(ScoringError):
        ball(scorer, match, extra_type="bye", runs_bat=1, extra_runs=1)
    with pytest.raises(ScoringError):
        ball(scorer, match, runs_bat=3, boundary=True)
    with pytest.raises(ScoringError):
        ball(scorer, match, extra_type="wide", wicket={"kind": "lbw"})
    with pytest.raises(ScoringError):
        ball(scorer, match, wicket={"kind": "caught"})  # fielder required
    with pytest.raises(ScoringError):
        ball(scorer, match, wicket={"kind": "bowled", "player_out": pa[1].pk})  # non-striker bowled
    assert Delivery.objects.count() == 0


def test_wickets_fall_of_wickets_and_new_batter(scorer):
    match, pa, pb = ready_match(scorer)
    ball(scorer, match, runs_bat=4)
    ball(scorer, match, wicket={"kind": "caught", "fielder": pb[0].pk})
    st = state_of(match)
    assert st.wickets == 1
    fow = st.fall_of_wickets[0]
    assert (fow["wicket"], fow["score"], fow["overs"], fow["player_id"]) == (1, 4, "0.2", pa[0].pk)
    line = st.batters[pa[0].pk]
    assert line.is_out and line.dismissal == "caught" and "b " in line.dismissal_text
    assert st.bowlers[pb[-1].pk].wickets == 1
    inn = innings(match)
    assert inn.striker_id is None and inn.non_striker_id == pa[1].pk
    with pytest.raises(ScoringError):
        ball(scorer, match)
    with pytest.raises(ScoringError):
        service.set_batter(scorer, match.pk, pa[0].pk, "striker")  # already out
    service.set_batter(scorer, match.pk, pa[2].pk, "striker")
    ball(scorer, match, runs_bat=1)
    st = state_of(match)
    assert st.partnerships[0]["runs"] == 4 and not st.partnerships[0]["unbeaten"]
    assert st.partnerships[-1]["runs"] == 1 and st.partnerships[-1]["unbeaten"]


def test_run_out_non_striker_with_crossing(scorer):
    match, pa, pb = ready_match(scorer)
    # Striker pa0 hits, one run completed, non-striker run out going for the second after crossing.
    ball(scorer, match, runs_bat=1, batters_crossed=True,
         wicket={"kind": "run_out", "player_out": pa[0].pk, "fielder": pb[3].pk})
    st = state_of(match)
    assert st.total == 1 and st.wickets == 1
    assert st.bowlers[pb[-1].pk].wickets == 0  # run outs are not credited to the bowler
    inn = innings(match)
    assert pa[0].pk not in (inn.striker_id, inn.non_striker_id)
    assert pa[1].pk in (inn.striker_id, inn.non_striker_id)


def test_all_out_completes_innings_and_target(scorer):
    match, pa, pb = ready_match(scorer, n=3)  # 3-a-side: 2 wickets end the innings
    ball(scorer, match, runs_bat=2)
    ball(scorer, match, wicket={"kind": "bowled"})
    service.set_batter(scorer, match.pk, pa[2].pk, "striker")
    ball(scorer, match, wicket={"kind": "lbw"})
    inn = innings(match, 1)
    assert inn.status == "completed" and inn.end_reason == "all_out"
    match.refresh_from_db()
    assert match.status == Match.Status.INNINGS_BREAK
    service.start_innings(scorer, match.pk, pb[0].pk, pb[1].pk, pa[0].pk)
    second = innings(match, 2)
    assert second.target == 3
    ball(scorer, match, runs_bat=4)
    match.refresh_from_db()
    assert match.status == Match.Status.COMPLETED
    assert match.result.kind == MatchResult.Kind.WICKETS and match.result.winner_id == second.batting_team_id
    assert match.result.margin == 2


def test_overs_complete_and_win_by_runs(scorer):
    match, pa, pb = ready_match(scorer, overs=1, n=5)
    bowl_over(scorer, match, (1, 1, 1, 1, 1, 1))
    first = innings(match, 1)
    assert first.status == "completed" and first.end_reason == "overs_complete" and first.total_runs == 6
    service.start_innings(scorer, match.pk, pb[0].pk, pb[1].pk, pa[2].pk)
    bowl_over(scorer, match, (0, 0, 0, 1, 1, 1))
    match.refresh_from_db()
    assert match.result.kind == MatchResult.Kind.RUNS and match.result.margin == 3
    assert match.result.summary.endswith("won by 3 runs")


def test_tie_goes_to_super_over(scorer):
    match, pa, pb = ready_match(scorer, overs=1, n=5)
    bowl_over(scorer, match, (1, 1, 1, 1, 1, 1))
    service.start_innings(scorer, match.pk, pb[0].pk, pb[1].pk, pa[2].pk)
    bowl_over(scorer, match, (1, 1, 1, 1, 1, 1))
    match.refresh_from_db()
    assert match.status == Match.Status.INNINGS_BREAK
    assert not MatchResult.objects.filter(match=match).exists()
    # Super over: team that batted second (B) bats first.
    service.start_innings(scorer, match.pk, pb[2].pk, pb[3].pk, pa[3].pk)
    so = innings(match, 3)
    assert so.is_super_over and so.batting_team_id == match.team_b_id and so.max_overs == 1 and so.max_wickets == 2
    bowl_over(scorer, match, (6, 0, 0, 0, 0, 0))
    service.start_innings(scorer, match.pk, pa[0].pk, pa[1].pk, pb[4].pk)
    ball(scorer, match, runs_bat=0, wicket={"kind": "bowled"})
    service.set_batter(scorer, match.pk, pa[2].pk, "striker")
    ball(scorer, match, runs_bat=0, wicket={"kind": "bowled"})
    match.refresh_from_db()
    assert match.result.kind == MatchResult.Kind.SUPER_OVER and match.result.winner_id == match.team_b_id


def test_tie_without_super_over(scorer):
    match, pa, pb = ready_match(scorer, overs=1, n=5, super_over_on_tie=False)
    bowl_over(scorer, match, (1, 1, 1, 1, 1, 1))
    service.start_innings(scorer, match.pk, pb[0].pk, pb[1].pk, pa[2].pk)
    bowl_over(scorer, match, (1, 1, 1, 1, 1, 1))
    match.refresh_from_db()
    assert match.result.kind == MatchResult.Kind.TIE and match.result.winner is None


def test_no_result(scorer):
    match, pa, pb = ready_match(scorer)
    ball(scorer, match, runs_bat=1)
    service.pause_match(scorer, match.pk, "Rain")
    with pytest.raises(ScoringError):
        ball(scorer, match, runs_bat=1)
    service.resume_match(scorer, match.pk)
    service.finish_match(scorer, match.pk, kind="no_result")
    match.refresh_from_db()
    assert match.status == Match.Status.COMPLETED and match.result.kind == "no_result"
    assert innings(match).end_reason == "interrupted"


def test_undo_restores_state(scorer):
    match, pa, pb = ready_match(scorer)
    ball(scorer, match, runs_bat=1)
    ball(scorer, match, wicket={"kind": "bowled"})
    inn = innings(match)
    assert inn.wickets == 1 and inn.striker_id is None
    service.undo_last(scorer, match.pk, "wrong button")
    inn.refresh_from_db()
    assert inn.wickets == 0 and inn.total_runs == 1 and inn.striker_id == pa[1].pk and inn.non_striker_id == pa[0].pk
    assert Delivery.objects.filter(voided=True).count() == 1
    corr = ScoringCorrection.objects.get()
    assert corr.action == "undo" and corr.before["wicket"]["kind"] == "bowled"
    # Undo works across an over boundary and restores the bowler.
    bowl_over(scorer, match, (0, 0, 0, 0, 0))
    assert innings(match).bowler_id is None
    service.undo_last(scorer, match.pk)
    assert innings(match).bowler_id == pb[-1].pk


def test_undo_reopens_completed_match(scorer):
    match, pa, pb = ready_match(scorer, overs=1, n=5)
    bowl_over(scorer, match, (1, 1, 1, 1, 1, 1))
    service.start_innings(scorer, match.pk, pb[0].pk, pb[1].pk, pa[2].pk)
    bowl_over(scorer, match, (4, 4))
    match.refresh_from_db()
    assert match.status == Match.Status.COMPLETED
    service.undo_last(scorer, match.pk)
    match.refresh_from_db()
    assert match.status == Match.Status.LIVE
    assert not MatchResult.objects.filter(match=match).exists()
    assert innings(match).status == "in_progress"


def test_edit_previous_delivery_replays_innings(scorer):
    match, pa, pb = ready_match(scorer)
    d1, _, _ = ball(scorer, match, runs_bat=1)
    ball(scorer, match, runs_bat=2)
    ball(scorer, match, runs_bat=0)
    # The first ball was actually a wide (+1): legal ball count shifts.
    service.edit_delivery(scorer, match.pk, d1.pk, {"extra_type": "wide", "runs_bat": 0, "extra_runs": 0}, "was a wide")
    st = state_of(match)
    assert st.total == 3 and st.legal_balls == 2 and st.wides == 1
    d1.refresh_from_db()
    assert d1.ball_in_over == 0
    later = Delivery.objects.filter(innings=innings(match), voided=False).order_by("sequence")
    assert [x.ball_in_over for x in later] == [0, 1, 2]
    corr = ScoringCorrection.objects.get(action="edit")
    assert corr.before["runs_bat"] == 1 and corr.after["wides"] == 1


def test_edit_cannot_create_inconsistent_history(scorer):
    match, pa, pb = ready_match(scorer)
    d1, _, _ = ball(scorer, match, runs_bat=0)
    ball(scorer, match, runs_bat=0)
    # pa0 faced ball 1 and is at the crease for ball 2; making ball 1 a wicket would put a dismissed batter in ball 2.
    with pytest.raises(ScoringError):
        service.edit_delivery(scorer, match.pk, d1.pk, {"wicket": {"kind": "bowled"}})
    assert not Delivery.objects.get(pk=d1.pk).is_wicket


def test_duplicate_event_and_stale_sequence(scorer):
    match, pa, pb = ready_match(scorer)
    cid = str(uuid.uuid4())
    d1, _, dup1 = service.record_delivery(scorer, match.pk, {"client_event_id": cid, "runs_bat": 1, "expected_sequence": 1})
    d2, _, dup2 = service.record_delivery(scorer, match.pk, {"client_event_id": cid, "runs_bat": 1, "expected_sequence": 1})
    assert d1.pk == d2.pk and not dup1 and dup2
    assert Delivery.objects.count() == 1
    with pytest.raises(ScoringConflict):
        service.record_delivery(scorer, match.pk, {"client_event_id": str(uuid.uuid4()), "runs_bat": 1, "expected_sequence": 1})
    assert Delivery.objects.count() == 1


def test_retired_hurt_can_return(scorer):
    match, pa, pb = ready_match(scorer)
    ball(scorer, match, runs_bat=2)
    service.retire_batter(scorer, match.pk, pa[0].pk, "retired_hurt")
    st = state_of(match)
    assert st.wickets == 0 and st.batters[pa[0].pk].retired_hurt
    service.set_batter(scorer, match.pk, pa[2].pk, "striker")
    ball(scorer, match, runs_bat=0, wicket={"kind": "bowled"})
    service.set_batter(scorer, match.pk, pa[0].pk, "striker")  # returns
    ball(scorer, match, runs_bat=1)
    st = state_of(match)
    assert st.batters[pa[0].pk].runs == 3 and not st.batters[pa[0].pk].retired_hurt


def test_last_man_stands(scorer):
    match, pa, pb = ready_match(scorer, n=3, last_man_stands=True)
    inn = innings(match)
    assert inn.max_wickets == 3
    ball(scorer, match, wicket={"kind": "bowled"})
    service.set_batter(scorer, match.pk, pa[2].pk, "striker")
    ball(scorer, match, wicket={"kind": "bowled"})
    inn.refresh_from_db()
    # Only pa[1] remains and bats alone.
    assert inn.striker_id == pa[1].pk and inn.non_striker_id is None
    ball(scorer, match, runs_bat=1)
    inn.refresh_from_db()
    assert inn.striker_id == pa[1].pk
    ball(scorer, match, wicket={"kind": "bowled"})
    inn.refresh_from_db()
    assert inn.status == "completed" and inn.end_reason == "all_out"


def test_disallowed_dismissal_by_local_rules(scorer):
    match, pa, pb = ready_match(scorer, disallowed_dismissals=["lbw"])
    with pytest.raises(ScoringError) as exc:
        ball(scorer, match, wicket={"kind": "lbw"})
    assert exc.value.code == "dismissal_disallowed"


def test_caught_new_batter_takes_strike(scorer):
    match, pa, pb = ready_match(scorer)
    ball(scorer, match, wicket={"kind": "caught", "fielder": pb[1].pk})
    inn = innings(match)
    assert inn.striker_id is None and inn.non_striker_id == pa[1].pk


def test_revised_overs_and_target(scorer):
    match, pa, pb = ready_match(scorer, overs=5, n=5)
    for over in range(5):
        if over:
            service.set_bowler(scorer, match.pk, pb[-1 - over].pk)
        bowl_over(scorer, match, (1, 1, 1, 1, 1, 1))
    service.start_innings(scorer, match.pk, pb[0].pk, pb[1].pk, pa[2].pk)
    service.pause_match(scorer, match.pk, "Rain")
    service.resume_match(scorer, match.pk)
    service.revise_innings(scorer, match.pk, max_overs=2, target=15, reason="rain")
    inn = innings(match, 2)
    assert inn.max_overs == 2 and inn.target == 15
    match.refresh_from_db()
    assert match.paused_seconds >= 0


def test_unassigned_scorer_cannot_score(scorer, db):
    from .conftest import make_user

    match, pa, pb = ready_match(scorer)
    other = make_user("intruder", "scorer")
    with pytest.raises(ScoringError) as exc:
        ball(other, match, runs_bat=4)
    assert exc.value.code == "forbidden"
