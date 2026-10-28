import random

import pytest

from core.management.commands.simulate_live import Simulator
from matches.models import Match

from .conftest import make_user, ready_match

pytestmark = pytest.mark.django_db(transaction=True)


def test_simulator_plays_a_whole_match_through_the_scoring_service():
    scorer = make_user("sim_scorer", role="scorer")
    match, _, _ = ready_match(scorer, n=6, overs=2)
    sim = Simulator(match.pk, scorer, rng=random.Random(7))
    steps = 0
    while sim.step():
        steps += 1
        assert steps < 400, "simulation did not finish"
    match.refresh_from_db()
    assert match.status == Match.Status.COMPLETED
    assert match.result.summary
    assert match.innings.filter(is_super_over=False).count() == 2
