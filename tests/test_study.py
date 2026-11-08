"""Check the experiment against the pinned publications and an independent update."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from flyflip.data import SOURCES, load_panel, verify
from flyflip.study import Protocol, encode, matrix, rewire, simulate, trial_plan


@pytest.fixture(scope="module")
def inputs():
    path = Path(__file__).resolve().parents[1] / "data/raw"
    return path, load_panel(path)


def test_published_inputs_and_selected_values(inputs):
    path, panel = inputs
    assert panel.counts["published_contacts"] == 6468
    assert (len(panel.receptors), len(panel.odor_ids)) == (18, 27)
    assert (len(panel.pn_ids), len(panel.kc_ids), len(panel.pn_index)) == (36, 1146, 2418)
    values = pd.read_csv(path / "door_response_matrix.csv", sep=";", index_col=0)
    contacts = pd.read_csv(path / "201001_bouton_claw_table.csv")
    source_edges = set(zip(contacts.pn_skid, contacts.kc_skid, strict=True))
    selected_edges = set(zip(panel.pn_ids[panel.pn_index], panel.kc_ids[panel.kc_index], strict=True))
    assert len(selected_edges) == len(panel.pn_index)
    assert selected_edges <= source_edges
    for index, glomerulus in enumerate(panel.pn_glomeruli):
        expected = values.loc[panel.odor_ids, panel.receptors[glomerulus]].to_numpy()
        np.testing.assert_array_equal(panel.responses[:, index], expected)


def test_checksum_rejects_modified_source(inputs, tmp_path):
    path, _ = inputs
    name = "door_mappings.csv"
    changed = tmp_path / name
    changed.write_bytes((path / name).read_bytes() + b"\n")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify(changed, SOURCES[name][2])


def test_rewire_preserves_degrees_and_changes_edge_set(inputs):
    _, panel = inputs
    protocol = Protocol()
    original = panel.kc_index.copy()
    moved, overlap = rewire(panel.pn_index, original, protocol.seed + 1, protocol.swaps_per_edge)
    assert 0 < overlap < 0.25
    np.testing.assert_array_equal(original, panel.kc_index)
    np.testing.assert_array_equal(np.bincount(moved), np.bincount(original))
    assert len(set(zip(panel.pn_index, moved, strict=True))) == len(original)
    again, _ = rewire(panel.pn_index, original, protocol.seed + 1, protocol.swaps_per_edge)
    np.testing.assert_array_equal(again, moved)


def test_encoder_preserves_ties_and_normalizes_nonzero_rows(inputs):
    _, panel = inputs
    protocol = Protocol()
    graph = matrix(panel.pn_index, panel.kc_index, (len(panel.pn_ids), len(panel.kc_ids)))
    features, active = encode(panel.responses, graph, protocol.active_fraction)
    assert (features >= 0).all()
    np.testing.assert_allclose(np.linalg.norm(features, axis=1), 1)
    assert (active >= np.ceil(graph.shape[1] * protocol.active_fraction)).all()
    assert (active < graph.shape[1]).all()


def test_kernel_update_matches_explicit_weight_update_on_measured_odors(inputs):
    _, panel = inputs
    protocol = Protocol()
    graph = matrix(panel.pn_index, panel.kc_index, (len(panel.pn_ids), len(panel.kc_ids)))
    features, _ = encode(panel.responses[:2], graph, protocol.active_fraction)
    plan = trial_plan(len(features), protocol)
    _, _, first_rewarded, explore, random_action = plan
    choices, rewards = simulate(features, plan, protocol)
    for episode in (0, protocol.replicates):
        weight = np.zeros(features.shape[1])
        for trial in range(2 * protocol.phase_trials):
            scores = features @ weight
            if explore[trial, episode] or abs(scores[0] - scores[1]) <= 1e-12:
                choice = random_action[trial, episode]
            else:
                choice = int(np.argmax(scores))
            target = first_rewarded[episode] ^ (trial >= protocol.phase_trials)
            reward = choice == target
            assert (choice, reward) == (choices[trial, episode], rewards[trial, episode])
            weight += protocol.learning_rate * (reward - scores[choice]) * features[choice]


def test_no_learning_stays_at_chance_and_reward_orders_balance(inputs):
    _, panel = inputs
    protocol = Protocol()
    plan = trial_plan(len(panel.odor_ids), protocol)
    pairs, pair_index, initial, _, random_action = plan
    orders = initial.reshape(len(pairs), 2 * protocol.replicates)
    assert (orders.sum(axis=1) == protocol.replicates).all()
    assert len(pair_index) == len(pairs) * 2 * protocol.replicates
    choices, rewarded = simulate(panel.responses, plan, protocol, learning=False)
    np.testing.assert_array_equal(choices, random_action)
    assert abs(rewarded.mean() - 0.5) < 0.01
