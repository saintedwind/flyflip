"""Fetch verified sources or run the experiment without network access."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import scipy

from .data import SOURCES, fetch, load_panel
from .lab import export_lab
from .replay import export_replay
from .study import Protocol, encode, matrix, rewire, simulate, summarize, trial_plan, unit_rows


def run(directory: Path):
    panel = load_panel(directory)
    protocol = Protocol()
    shape = (len(panel.pn_ids), len(panel.kc_ids))
    observed = matrix(panel.pn_index, panel.kc_index, shape)
    plan = trial_plan(len(panel.odor_ids), protocol)
    pairs, pair_index, initial_target, _, _ = plan
    receptor_indices = [panel.pn_glomeruli.index(glom) for glom in panel.receptors]
    receptor_features = unit_rows(panel.responses[:, receptor_indices])
    pair_similarity = (receptor_features[pairs[:, 0]] * receptor_features[pairs[:, 1]]).sum(axis=1)
    # Choose the demo by input similarity, independently of learning outcomes.
    demo_pair = int(np.argsort(pair_similarity, kind="stable")[len(pairs) // 2])
    demo_episode = int(np.flatnonzero((pair_index == demo_pair) & (initial_target == 0))[0])
    tracks = {}

    def evaluate(name, features, *, learning=True, trace=False):
        choices, rewards = simulate(features, plan, protocol, learning=learning)
        if trace:
            tracks[name] = {
                "choices": choices[:, demo_episode].tolist(),
                "rewarded": rewards[:, demo_episode].tolist(),
            }
        return summarize(rewards, plan, protocol)

    actual_features, active = encode(panel.responses, observed, protocol.active_fraction)
    actual = evaluate("observed", actual_features, trace=True)
    actual["mean_active_kenyon_cells"] = float(active.mean())
    controls = []
    for i in range(protocol.rewires):
        seed = protocol.seed + 1 + i
        targets, overlap = rewire(panel.pn_index, panel.kc_index, seed, protocol.swaps_per_edge)
        rewired = matrix(panel.pn_index, targets, shape)
        if any((rewired.sum(axis=axis) != observed.sum(axis=axis)).any() for axis in (0, 1)):
            raise AssertionError("Rewire changed a node degree")
        features, active = encode(panel.responses, rewired, protocol.active_fraction)
        result = evaluate("rewired", features, trace=i == 0)
        controls.append({"seed": seed, "edge_overlap": overlap,
                         "mean_active_kenyon_cells": float(active.mean()), **result})

    direct = evaluate("direct_receptor", receptor_features)
    no_learning = evaluate("no_learning", actual_features, learning=False)
    early = [item["first_after_switch"] for item in controls]
    return {
        "schema": "flyflip-study-v1",
        "scope": "Published adult FAFB wiring and DoOR consensus measurements; simulated choices and rewards.",
        "sources": {name: {"repository": repo, "revision": commit, "sha256": digest}
                    for name, (repo, commit, digest) in SOURCES.items()},
        "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                    "scipy": scipy.__version__, "pandas": pd.__version__},
        "protocol": asdict(protocol),
        "panel": {**panel.counts, "projection_neurons": shape[0], "kenyon_cells": shape[1],
                  "binary_edges": len(panel.pn_index), "odor_count": len(panel.odor_ids),
                  "receptors_by_glomerulus": panel.receptors,
                  "odors": [{"inchikey": i, "name": n}
                            for i, n in zip(panel.odor_ids, panel.odor_names, strict=True)],
                  "pairs": pairs.tolist()},
        "observed": actual,
        "rewired": controls,
        "rewired_early_summary": {"mean": float(np.mean(early)), "min": min(early), "max": max(early),
                                  "observed_minus_mean": actual["first_after_switch"] - float(np.mean(early))},
        "direct_receptor": direct,
        "no_learning": no_learning,
        "demo": {"pair_index": demo_pair, "episode_index": demo_episode,
                 "odor_names": [panel.odor_names[i] for i in pairs[demo_pair]],
                 "odor_ids": [panel.odor_ids[i] for i in pairs[demo_pair]],
                 "tracks": tracks},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch", help="Retrieve exact public source files and verify their hashes")
    experiment = commands.add_parser("run", help="Run the CPU experiment on verified local inputs")
    experiment.add_argument("--output", type=Path, default=Path("results/study.json"))
    replay = commands.add_parser("replay", help="Export an offline replay of a saved experiment")
    replay.add_argument("--study", type=Path, default=Path("results/study.json"))
    replay.add_argument("--output", type=Path, default=Path("results/replay.html"))
    lab = commands.add_parser("lab", help="Build the standalone bilingual browser lab")
    lab.add_argument("--study", type=Path, default=Path("results/study.json"))
    lab.add_argument("--output", type=Path, default=Path("results/lab.html"))
    args = parser.parse_args()
    if args.command == "fetch":
        fetch(args.data)
        print(f"Verified {len(SOURCES)} upstream files in {args.data}")
        return
    if args.command == "replay":
        export_replay(args.study, args.output)
        print(f"Wrote {args.output}")
        return
    if args.command == "lab":
        export_lab(args.data, args.study, args.output)
        print(f"Wrote {args.output}")
        return
    result = run(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{result['panel']['odor_count']} odors, {result['observed']['episodes']:,} episodes per condition")
    print(f"Observed early reversal: {result['observed']['first_after_switch']:.2%}")
    print(f"Mean rewired early reversal: {result['rewired_early_summary']['mean']:.2%}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
