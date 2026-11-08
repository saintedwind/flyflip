"""Build the browser lab from verified inputs and a recorded benchmark."""

from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from .data import SOURCES, load_panel
from .study import Protocol, encode, matrix, rewire, unit_rows


def lab_payload(data: Path, study: Path):
    contents = study.read_bytes()
    report = json.loads(contents)
    if report.get("schema") != "flyflip-study-v1":
        raise ValueError("Unknown study format")
    for name, (repo, revision, digest) in SOURCES.items():
        if report["sources"].get(name) != {"repository": repo, "revision": revision, "sha256": digest}:
            raise ValueError(f"Benchmark source differs from {name}")

    protocol = Protocol(**report["protocol"])
    panel = load_panel(data)
    if [item["inchikey"] for item in report["panel"]["odors"]] != panel.odor_ids:
        raise ValueError("Benchmark odor panel differs from the verified input panel")
    seeds = [item["seed"] for item in report["rewired"]]
    if seeds != list(range(protocol.seed + 1, protocol.seed + 1 + protocol.rewires)):
        raise ValueError("Benchmark control seeds differ from the protocol")
    shape = (len(panel.pn_ids), len(panel.kc_ids))

    def kernel(targets):
        graph = matrix(panel.pn_index, targets, shape)
        features, _ = encode(panel.responses, graph, protocol.active_fraction)
        return (features @ features.T).tolist()

    indices = [panel.pn_glomeruli.index(glomerulus) for glomerulus in panel.receptors]
    direct = unit_rows(panel.responses[:, indices])
    observed = kernel(panel.kc_index)
    controls = []
    for seed in seeds:
        targets, _ = rewire(panel.pn_index, panel.kc_index, seed, protocol.swaps_per_edge)
        controls.append(kernel(targets))

    keys = ("late_before_switch", "first_after_switch", "late_after_switch", "trial_accuracy")

    def recorded(result):
        return {key: result[key] for key in keys}

    average_control = {
        key: np.mean([item[key] for item in report["rewired"]], axis=0).tolist() for key in keys
    }
    return {
        "schema": "flyflip-lab-v1",
        "benchmark_sha256": sha256(contents).hexdigest(),
        "protocol": report["protocol"],
        "sources": report["sources"],
        "panel": {"odors": report["panel"]["odors"], "edges": len(panel.pn_index),
                  "channels": len(indices), "kenyon_cells": shape[1], "projection_neurons": shape[0]},
        "initial_pair": report["panel"]["pairs"][report["demo"]["pair_index"]],
        "kernels": {"observed": observed, "direct": (direct @ direct.T).tolist(), "controls": controls},
        "benchmark": {
            "episodes": report["observed"]["episodes"], "pairs": len(report["panel"]["pairs"]),
            "observed": recorded(report["observed"]), "rewired": average_control,
            "direct": recorded(report["direct_receptor"]), "chance": recorded(report["no_learning"]),
            "control_range": [report["rewired_early_summary"][key] for key in ("min", "max")],
        },
    }


def export_lab(data: Path, study: Path, output: Path):
    payload = json.dumps(lab_payload(data, study), separators=(",", ":"), allow_nan=False)
    template = Path(__file__).with_name("lab.html").read_text(encoding="utf-8")
    for marker, code in (("__FLYFLIP_MODEL__", "lab-model.js"), ("__FLYFLIP_UI__", "lab-ui.js")):
        template = template.replace(marker, Path(__file__).with_name(code).read_text(encoding="utf-8"), 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace("__FLYFLIP_LAB__", payload.replace("<", "\\u003c"), 1),
                      encoding="utf-8", newline="\n")
