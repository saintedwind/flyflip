"""Sparse sensory encoding and paired online reversal trials."""

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from scipy.sparse import csr_matrix


@dataclass(frozen=True)
class Protocol:
    phase_trials: int = 60
    early_trials: int = 20
    learning_rate: float = 0.30
    exploration: float = 0.15
    active_fraction: float = 0.10
    replicates: int = 16
    rewires: int = 12
    swaps_per_edge: int = 5
    seed: int = 1729


def matrix(pn, kc, shape):
    """One binary edge per observed PN/KC pair, regardless of contact count."""
    result = csr_matrix((np.ones(len(pn)), (pn, kc)), shape=shape)
    result.data.fill(1.0)
    return result


def rewire(pn, kc, seed, swaps_per_edge):
    """Swap targets of distinct edges, preserving every PN and KC degree."""
    rng = np.random.default_rng(seed)
    targets = kc.copy()
    observed = {(int(a), int(b)) for a, b in zip(pn, kc, strict=True)}
    edges = observed.copy()
    required = len(pn) * swaps_per_edge
    accepted = attempted = 0
    while accepted < required and attempted < required * 20:
        attempted += 1
        i, j = rng.integers(len(pn), size=2)
        a, b = int(pn[i]), int(pn[j])
        x, y = int(targets[i]), int(targets[j])
        if a == b or x == y or (a, y) in edges or (b, x) in edges:
            continue
        edges.remove((a, x))
        edges.remove((b, y))
        edges.update(((a, y), (b, x)))
        targets[i], targets[j] = y, x
        accepted += 1
    if accepted != required:
        raise ValueError("Degree-preserving rewire did not reach its swap budget")
    return targets, len(edges & observed) / len(observed)


def unit_rows(values):
    norm = np.linalg.norm(values, axis=1, keepdims=True)
    return np.divide(values, norm, out=np.zeros_like(values), where=norm > 0)


def encode(responses, connectivity, active_fraction):
    """Average observed inputs per KC and retain its highest positive responses."""
    degree = np.asarray(connectivity.sum(axis=0)).ravel()
    drive = (connectivity.T @ responses.T).T / np.maximum(degree, 1)
    keep = max(1, int(np.ceil(active_fraction * drive.shape[1])))
    cutoff = np.partition(drive, -keep, axis=1)[:, -keep, None]
    # Keep ties at the boundary, rather than break ties by arbitrary neuron IDs.
    sparse = np.where((drive >= cutoff) & (drive > 0), drive, 0)
    return unit_rows(sparse), np.count_nonzero(sparse, axis=1)


def trial_plan(odor_count, protocol):
    """All unordered pairs, both reward orders and common random actions."""
    pairs = np.asarray(list(combinations(range(odor_count), 2)), dtype=int)
    pair_index = np.repeat(np.arange(len(pairs)), 2 * protocol.replicates)
    first_rewarded = np.tile(np.repeat([0, 1], protocol.replicates), len(pairs))
    rng = np.random.default_rng(protocol.seed)
    shape = (2 * protocol.phase_trials, len(pair_index))
    explore = rng.random(shape) < protocol.exploration
    random_action = rng.integers(0, 2, size=shape, dtype=np.int8)
    return pairs, pair_index, first_rewarded, explore, random_action


def simulate(features, plan, protocol, *, learning=True):
    """Fit one linear readout online with reward prediction error.

    Updating the two scores with their feature Gram matrix is exactly the
    linear weight update, without storing one parameter vector per episode.
    """
    pairs, pair_index, first_rewarded, explore, random_action = plan
    feature_pairs = features[pairs]
    grams = feature_pairs @ feature_pairs.transpose(0, 2, 1)
    gram = grams[pair_index]
    scores = np.zeros((len(pair_index), 2), dtype=float)
    choices = np.empty(explore.shape, dtype=np.int8)
    rewarded = np.empty(explore.shape, dtype=bool)
    episode = np.arange(len(pair_index))
    for trial in range(len(explore)):
        greedy = (scores[:, 1] > scores[:, 0]).astype(np.int8)
        tied = np.abs(scores[:, 1] - scores[:, 0]) <= 1e-12
        choice = np.where(explore[trial] | tied, random_action[trial], greedy)
        target = first_rewarded if trial < protocol.phase_trials else 1 - first_rewarded
        reward = choice == target
        choices[trial] = choice
        rewarded[trial] = reward
        if learning:
            error = reward - scores[episode, choice]
            scores += protocol.learning_rate * error[:, None] * gram[episode, :, choice]
    return choices, rewarded


def summarize(rewarded, plan, protocol):
    pairs, pair_index, _, _, _ = plan
    switch, width = protocol.phase_trials, protocol.early_trials
    recovery_width = 10
    after = rewarded[switch:].astype(np.int8)
    windows = np.lib.stride_tricks.sliding_window_view(after, recovery_width, axis=0)
    reached = windows.sum(axis=-1) >= 8
    observed = reached.any(axis=0)
    latency = reached.argmax(axis=0) + recovery_width
    pair_early = rewarded[switch : switch + width].reshape(width, len(pairs), -1)
    return {
        "episodes": int(len(pair_index)),
        "late_before_switch": float(rewarded[switch - width : switch].mean()),
        "first_after_switch": float(rewarded[switch : switch + width].mean()),
        "late_after_switch": float(rewarded[-width:].mean()),
        "recovered_fraction": float(observed.mean()),
        "median_recovery_trials_among_recovered": (
            float(np.median(latency[observed])) if observed.any() else None
        ),
        "trial_accuracy": rewarded.mean(axis=1).tolist(),
        "pair_first_after_switch": pair_early.mean(axis=(0, 2)).tolist(),
    }
