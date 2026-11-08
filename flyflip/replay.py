"""Build a self-contained browser replay from a recorded study."""

import json
from pathlib import Path

import numpy as np


def export_replay(study: Path, output: Path):
    report = json.loads(study.read_text(encoding="utf-8"))
    if report.get("schema") != "flyflip-study-v1":
        raise ValueError("Unknown study format")
    payload = {
        "switch": report["protocol"]["phase_trials"],
        "odors": report["demo"]["odor_names"],
        "tracks": report["demo"]["tracks"],
        "trials": {"observed": report["observed"]["trial_accuracy"],
                   "rewired": np.mean([run["trial_accuracy"] for run in report["rewired"]], axis=0).tolist(),
                   "direct": report["direct_receptor"]["trial_accuracy"]},
        "early": [report["observed"]["first_after_switch"],
                  report["rewired_early_summary"]["mean"],
                  report["direct_receptor"]["first_after_switch"]],
        "episodes": report["observed"]["episodes"],
        "odorCount": report["panel"]["odor_count"],
        "rewireCount": report["protocol"]["rewires"],
    }
    template = Path(__file__).with_name("replay.html").read_text(encoding="utf-8")
    encoded = json.dumps(payload, allow_nan=False).replace("<", "\\u003c")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace("__FLYFLIP_STUDY__", encoded, 1), encoding="utf-8", newline="\n")
