import numpy as np
import pytest

from flyflip.study import Protocol, simulate, summarize, trial_plan


@pytest.mark.parametrize("settings,field", [
    ({"phase_trials": 9}, "phase_trials"),
    ({"phase_trials": 10.5}, "phase_trials"),
    ({"phase_trials": True}, "phase_trials"),
    ({"early_trials": 0}, "early_trials"),
    ({"early_trials": -1}, "early_trials"),
    ({"early_trials": 61}, "early_trials"),
    ({"early_trials": 2.5}, "early_trials"),
    ({"early_trials": True}, "early_trials"),
])
def test_invalid_summary_windows_fail_before_simulation(settings, field):
    with pytest.raises(ValueError, match=field):
        Protocol(**settings)


@pytest.mark.parametrize("width", [1, 10])
def test_smallest_valid_phase_produces_finite_summary(width):
    protocol = Protocol(phase_trials=10, early_trials=width, replicates=1)
    plan = trial_plan(2, protocol)
    _, rewards = simulate(np.eye(2), plan, protocol)
    result = summarize(rewards, plan, protocol)
    assert result["episodes"] == 2
    assert len(result["trial_accuracy"]) == 20
    for key in ("late_before_switch", "first_after_switch", "late_after_switch", "recovered_fraction"):
        assert 0 <= result[key] <= 1
    np.testing.assert_allclose(result["first_after_switch"], rewards[10:10 + width].mean())


@pytest.mark.parametrize("field", ["learning_rate", "exploration", "active_fraction"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "0.3"])
def test_protocol_rejects_nonfinite_or_non_numeric_values(field, value):
    with pytest.raises(ValueError, match=field):
        Protocol(**{field: value})


@pytest.mark.parametrize("field,value", [("learning_rate", -0.1), ("exploration", -0.1),
                                        ("exploration", 1.1), ("active_fraction", 0),
                                        ("active_fraction", 1.1)])
def test_protocol_rejects_out_of_range_values(field, value):
    with pytest.raises(ValueError, match=field):
        Protocol(**{field: value})


@pytest.mark.parametrize("exploration", [0, 1])
def test_probability_boundaries_and_zero_learning(exploration):
    protocol = Protocol(phase_trials=10, early_trials=1, replicates=1,
                        exploration=exploration, learning_rate=0, active_fraction=1)
    plan = trial_plan(2, protocol)
    assert np.all(plan[3] == bool(exploration))
    choices, rewards = simulate(np.eye(2), plan, protocol)
    expected_choices, expected_rewards = simulate(np.eye(2), plan, protocol, learning=False)
    np.testing.assert_array_equal(choices, expected_choices)
    np.testing.assert_array_equal(rewards, expected_rewards)
