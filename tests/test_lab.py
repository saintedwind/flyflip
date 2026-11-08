"""Check the offline artifact and browser simulation on measured odor pairs."""

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np
import pytest

from flyflip.data import load_panel
from flyflip.lab import export_lab
from flyflip.study import Protocol, encode, matrix, rewire, simulate, unit_rows


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/raw"
STUDY = ROOT / "results/study.json"


@pytest.fixture(scope="module")
def offline(tmp_path_factory):
    output = tmp_path_factory.mktemp("flyflip-lab") / "lab.html"
    export_lab(DATA, STUDY, output)
    return output


def test_offline_export_embeds_verified_reference(offline):
    html = offline.read_text(encoding="utf-8")
    payload = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', html).group(1))
    report = json.loads(STUDY.read_bytes())
    assert payload["benchmark_sha256"] == sha256(STUDY.read_bytes()).hexdigest()
    assert payload["sources"] == report["sources"]
    assert payload["panel"]["odors"] == report["panel"]["odors"]
    assert payload["benchmark"]["observed"]["trial_accuracy"] == report["observed"]["trial_accuracy"]
    assert payload["benchmark"]["rewired"]["first_after_switch"] == report["rewired_early_summary"]["mean"]
    assert len(payload["kernels"]["controls"]) == report["protocol"]["rewires"]
    assert "__FLYFLIP_" not in html and not re.search(r"<script[^>]+\bsrc=", html)


def test_browser_and_python_agree_on_measured_pairs(offline):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the cross-runtime test")
    script = r"""
    const fs = require('node:fs');
    const model = require(process.argv[1]);
    const html = fs.readFileSync(process.argv[2], 'utf8');
    const data = JSON.parse(html.match(/<script type="application\/json" id="data">(.*?)<\/script>/s)[1]);
    const cases = [[data.initial_pair, 0, 1729], [[26, 0], 1, 42], [[8, 13], 0, 4294967295]];
    const outputs = cases.map(([pair, initial, seed]) => ({
      result: model.run(data, pair, initial, seed),
      draws: Array.from(model.plan(data.protocol, seed).random)
    }));
    if (JSON.stringify(model.run(data, ...cases[0])) !== JSON.stringify(outputs[0].result)) process.exit(2);
    try { model.run(data, [0, 0], 0, 1729); process.exit(3); } catch (error) {
      if (!(error instanceof RangeError)) throw error;
    }
    console.log(JSON.stringify(outputs));
    """
    output = subprocess.run([node, "-e", script, str(ROOT / "flyflip/lab-model.js"), str(offline)],
                            check=True, capture_output=True, text=True, encoding="utf-8", timeout=30)
    protocol = Protocol()
    panel = load_panel(DATA)
    shape = (len(panel.pn_ids), len(panel.kc_ids))

    def features(targets):
        graph = matrix(panel.pn_index, targets, shape)
        return encode(panel.responses, graph, protocol.active_fraction)[0]

    indices = [panel.pn_glomeruli.index(glomerulus) for glomerulus in panel.receptors]
    observed = features(panel.kc_index)
    direct = unit_rows(panel.responses[:, indices])
    controls = []
    for seed in range(protocol.seed + 1, protocol.seed + 1 + protocol.rewires):
        targets, _ = rewire(panel.pn_index, panel.kc_index, seed, protocol.swaps_per_edge)
        controls.append(features(targets))

    for case in json.loads(output.stdout):
        result = case["result"]
        episodes = result["episodes"]
        first = result["initial"] ^ (np.arange(episodes) >= protocol.replicates)
        draws = np.asarray(case["draws"], dtype=np.uint32).reshape(-1, episodes, 2)
        plan = (np.array([result["pair"]]), np.zeros(episodes, dtype=int), first,
                draws[:, :, 0] / 2**32 < protocol.exploration, draws[:, :, 1] >> 31)
        choice, rewards = simulate(observed, plan, protocol)
        np.testing.assert_array_equal(result["curves"]["observed"], rewards.mean(axis=1))
        trace = result["tracks"]["observed"]
        np.testing.assert_array_equal([item["choice"] for item in trace], choice[:, 0])
        np.testing.assert_array_equal([item["reward"] for item in trace], rewards[:, 0])
        np.testing.assert_array_equal([item["target"] for item in trace],
                                      first[0] ^ (np.arange(len(trace)) >= protocol.phase_trials))
        _, rewards = simulate(direct, plan, protocol)
        np.testing.assert_array_equal(result["curves"]["direct"], rewards.mean(axis=1))
        rewired = [simulate(control, plan, protocol)[1].mean(axis=1) for control in controls]
        np.testing.assert_allclose(result["curves"]["rewired"], np.mean(rewired, axis=0), rtol=0, atol=1e-15)
