"""Pin the upstream tables and extract a complete, attributable odor panel."""

import base64
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


BOCK_COMMIT = "96fb0de1833539a0643ecc136b8a0dcd50d34932"
DOOR_COMMIT = "db323a496577c4b4a72b5c2fcd1859e07521ffb5"
SOURCES = {
    "201001_bouton_claw_table.csv": (
        "bocklab/pn_kc", BOCK_COMMIT,
        "924c98b8e2e4c0bb05dbb29cdfb394e3c26acd67360443d48cd4bb629d5f538c",
    ),
    "door_mappings.csv": (
        "ropensci/DoOR.data", DOOR_COMMIT,
        "1197c492e769b1b587c907c5b750ffa2507d7e6c9fe9dfcb2ee8603871e00912",
    ),
    "door_response_matrix.csv": (
        "ropensci/DoOR.data", DOOR_COMMIT,
        "bc2aa5414ff54d3a1399f5fe171e154bcadc754bcf323a3c27711a54f70848e2",
    ),
    "odor.csv": (
        "ropensci/DoOR.data", DOOR_COMMIT,
        "a31d1841cf90ce23ec149760a5efa38eae02de7820bb2300c3a7dba221745940",
    ),
}


@dataclass(frozen=True)
class Panel:
    odor_ids: list[str]
    odor_names: list[str]
    receptors: dict[str, str]
    pn_ids: np.ndarray
    kc_ids: np.ndarray
    pn_glomeruli: list[str]
    pn_index: np.ndarray
    kc_index: np.ndarray
    responses: np.ndarray
    counts: dict[str, int]


def verify(path, expected):
    if sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"SHA-256 mismatch for {path.name}")


def fetch(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name, (repo, commit, expected) in SOURCES.items():
        path = directory / name
        if path.is_file():
            verify(path, expected)
            continue
        url = f"https://api.github.com/repos/{repo}/contents/data/{name}?ref={commit}"
        request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "FlyFlip"})
        with urlopen(request, timeout=45) as response:
            item = json.load(response)
        if item.get("encoding") != "base64" or item.get("name") != name:
            raise ValueError(f"Unexpected upstream response for {name}")
        contents = base64.b64decode("".join(item["content"].split()), validate=True)
        if sha256(contents).hexdigest() != expected:
            raise ValueError(f"SHA-256 mismatch for {name}")
        temporary = path.with_suffix(".partial")
        temporary.write_bytes(contents)
        temporary.replace(path)


def load_panel(directory: Path, min_odors: int = 24) -> Panel:
    for name, (_, _, expected) in SOURCES.items():
        verify(directory / name, expected)
    contacts = pd.read_csv(directory / "201001_bouton_claw_table.csv")
    mapping = pd.read_csv(directory / "door_mappings.csv", sep=";", index_col=0)
    values = pd.read_csv(directory / "door_response_matrix.csv", sep=";", index_col=0)
    metadata = pd.read_csv(directory / "odor.csv", sep=";", index_col=0)

    # SFR and other non-compound controls do not have an InChIKey.
    odor_names = metadata.dropna(subset=["InChIKey", "Name"]).set_index("InChIKey")["Name"]
    if not odor_names.index.is_unique or not values.index.is_unique:
        raise ValueError("Non-unique odor identifiers")
    chemical = values.index.str.fullmatch(r"[A-Z]{14}-[A-Z]{10}-[A-Z]")
    values = values.loc[chemical & values.index.isin(odor_names.index)]

    candidates = mapping.loc[
        mapping.receptor.isin(values.columns) & mapping.glomerulus.isin(contacts.pn_type),
        ["glomerulus", "receptor"],
    ].drop_duplicates()
    one_to_one = candidates.loc[
        ~candidates.glomerulus.duplicated(keep=False) & ~candidates.receptor.duplicated(keep=False)
    ].copy()
    one_to_one["coverage"] = one_to_one.receptor.map(values.notna().sum())
    ranked = one_to_one.sort_values(["coverage", "glomerulus"], ascending=[False, True])
    # Only data availability determines the panel, before any model is scored.
    selected = next(
        (ranked.iloc[:n] for n in range(len(ranked), 7, -1)
         if len(values[ranked.receptor.iloc[:n]].dropna()) >= min_odors),
        None,
    )
    if selected is None:
        raise ValueError("Insufficient complete chemical responses across mapped glomeruli")
    receptors = dict(zip(selected.glomerulus, selected.receptor, strict=True))
    complete = values[list(receptors.values())].dropna().sort_index()

    subset = contacts[contacts.pn_type.isin(receptors)]
    pns = subset[["pn_skid", "pn_type"]].drop_duplicates().sort_values("pn_skid")
    if pns.pn_skid.duplicated().any():
        raise ValueError("A projection neuron has conflicting glomerulus annotations")
    pairs = subset[["pn_skid", "kc_skid"]].drop_duplicates().sort_values(["pn_skid", "kc_skid"])
    pn_ids = pns.pn_skid.to_numpy(dtype=np.int64)
    kc_ids = np.sort(pairs.kc_skid.unique()).astype(np.int64)
    responses = complete[[receptors[glom] for glom in pns.pn_type]].to_numpy(dtype=float)
    if not np.isfinite(responses).all() or not ((0 <= responses) & (responses <= 1)).all():
        raise ValueError("Expected finite normalized DoOR responses in [0, 1]")

    return Panel(
        list(complete.index), list(odor_names.loc[complete.index]), receptors,
        pn_ids, kc_ids, list(pns.pn_type),
        np.searchsorted(pn_ids, pairs.pn_skid), np.searchsorted(kc_ids, pairs.kc_skid),
        responses,
        {
            "published_contacts": len(contacts),
            "published_projection_neurons": contacts.pn_skid.nunique(),
            "published_kenyon_cells": contacts.kc_skid.nunique(),
            "chemical_rows_with_metadata": len(values),
            "unambiguous_glomeruli": len(ranked),
            "selected_contacts": len(subset),
        },
    )
