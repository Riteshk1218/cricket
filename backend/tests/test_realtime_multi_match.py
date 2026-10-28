"""Four simultaneous matches: independent scoring, state and WebSocket groups."""
import threading
import uuid

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from config.asgi import application
from matches.engine import service

from .conftest import ball, innings, make_tournament, make_user, ready_match


def _four_matches():
    scorers = [make_user(f"scorer_{i}", "scorer") for i in range(4)]
    matches = []
    for i, s in enumerate(scorers):
        match, pa, pb = ready_match(s)
        matches.append((match, s, pa, pb))
    return matches


@pytest.mark.django_db
def test_scoring_one_match_never_changes_another():
    matches = _four_matches()
    (m1, s1, *_), (m2, s2, *_), (m3, s3, *_), (m4, s4, *_) = matches
    ball(s1, m1, runs_bat=4)
    ball(s2, m2, runs_bat=6)
    ball(s2, m2, extra_type="wide")
    ball(s3, m3, wicket={"kind": "bowled"})
    totals = [innings(m).total_runs for m, *_ in matches]
    wickets = [innings(m).wickets for m, *_ in matches]
    assert totals == [4, 7, 0, 0]
    assert wickets == [0, 0, 1, 0]
    # A scorer assigned to match 1 cannot score match 4.
    from core.exceptions import ScoringError

    with pytest.raises(ScoringError):
        ball(s1, m4, runs_bat=1)
    # Undo in match 2 leaves match 1 untouched.
    service.undo_last(s2, m2.pk)
    assert innings(m2).total_runs == 6 and innings(m1).total_runs == 4
    versions = {m.pk: m.version for m in [x[0] for x in matches]}
    for m, *_ in matches:
        m.refresh_from_db()
    assert matches[3][0].version == versions[m4.pk]  # untouched match never bumped


@pytest.mark.django_db(transaction=True)
def test_concurrent_scorers_cannot_record_the_same_delivery():
    """Two scorers submit the 'next ball' at the same time; exactly one wins."""
    s = make_user("lead", "scorer")
    match, pa, pb = ready_match(s)
    second = make_user("backup", "scorer")
    from matches.models import Delivery, ScorerAssignment

    ScorerAssignment.objects.create(match=match, scorer=second)
    results = []
    barrier = threading.Barrier(2)

    def submit(user):
        from django.db import connection

        barrier.wait()
        try:
            service.record_delivery(user, match.pk, {"client_event_id": str(uuid.uuid4()), "runs_bat": 1,
                                                     "expected_sequence": 1})
            results.append("ok")
        except Exception as exc:  # noqa: BLE001
            results.append(type(exc).__name__)
        finally:
            connection.close()

    threads = [threading.Thread(target=submit, args=(u,)) for u in (s, second)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == ["ScoringConflict", "ok"]
    assert Delivery.objects.filter(innings__match=match, voided=False).count() == 1


@pytest.mark.django_db(transaction=True)
async def test_websocket_updates_are_isolated_per_match():
    matches = await database_sync_to_async(_four_matches)()
    comms = []
    for match, *_ in matches:
        comm = WebsocketCommunicator(application, f"/ws/matches/{match.pk}/?client=web")
        connected, _ = await comm.connect()
        assert connected
        first = await comm.receive_json_from(timeout=5)
        assert first["type"] == "snapshot" and first["snapshot"]["id"] == match.pk
        comms.append(comm)

    async def drain(comm):
        # receive_nothing() does not cancel the consumer on timeout (receive_* with a timeout does).
        msgs = []
        while not await comm.receive_nothing(timeout=0.3):
            msgs.append(await comm.receive_json_from())
        return msgs

    for comm in comms:
        await drain(comm)  # viewer-count messages

    m1, s1, *_ = matches[0]
    await database_sync_to_async(ball)(s1, m1, runs_bat=6)
    msgs = [m for m in await drain(comms[0]) if m["type"] == "update"]
    assert len(msgs) == 1
    update = msgs[0]
    assert update["snapshot"]["id"] == m1.pk
    assert update["snapshot"]["current"]["score"] == "6/0"
    assert update["event"]["highlight"] == "six"
    for comm in comms[1:]:
        assert [m for m in await drain(comm) if m["type"] == "update"] == []

    m3, s3, *_ = matches[2]
    await database_sync_to_async(ball)(s3, m3, wicket={"kind": "bowled"})
    msgs = [m for m in await drain(comms[2]) if m["type"] == "update"]
    assert msgs and msgs[-1]["event"]["highlight"] == "wicket"
    assert [m for m in await drain(comms[0]) if m["type"] == "update"] == []

    for comm in comms:
        await comm.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_viewer_counts_and_ping():
    match, *_ = (await database_sync_to_async(lambda: ready_match(make_user("sc", "scorer")))())
    a = WebsocketCommunicator(application, f"/ws/matches/{match.pk}/?client=android")
    b = WebsocketCommunicator(application, f"/ws/matches/{match.pk}/")
    await a.connect()
    snap = await a.receive_json_from()
    assert snap["viewers"] == 1
    await b.connect()
    snap_b = await b.receive_json_from()
    assert snap_b["viewers"] == 2
    await b.send_json_to({"type": "ping"})
    msgs = []
    while not await b.receive_nothing(timeout=0.5):
        msgs.append(await b.receive_json_from())
    assert any(m["type"] == "pong" for m in msgs)
    await b.disconnect()
    from analytics.services import viewers_for_match

    assert await database_sync_to_async(viewers_for_match)(match.pk) == 1
    await a.disconnect()
    assert await database_sync_to_async(viewers_for_match)(match.pk) == 0


@pytest.mark.django_db(transaction=True)
async def test_unknown_match_socket_is_rejected():
    await database_sync_to_async(make_tournament)()
    comm = WebsocketCommunicator(application, "/ws/matches/999999/")
    connected, code = await comm.connect()
    assert not connected or code == 4404
