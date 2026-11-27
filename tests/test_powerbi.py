"""Static consistency checks for the Power BI project (no Power BI needed)."""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PBI = ROOT / "Renewable_PowerBI"
MODEL = PBI / "Renewable_Energy.SemanticModel" / "definition"
REPORT = PBI / "Renewable_Energy.Report" / "definition"
NAME = r"('[^']+'|[^\s=]+)"


def read(path):
    return path.read_text(encoding="utf-8-sig")


def model_fields(kind):
    """Return {(table, name)} for every 'column' or 'measure' in the model."""
    fields = set()
    for path in (MODEL / "tables").glob("*.tmdl"):
        for name in re.findall(rf"^\t{kind} {NAME}", read(path), re.M):
            fields.add((path.stem, name.strip("'")))
    return fields


def visual_fields(node):
    """Yield (kind, table, name) for every field reference in a visual."""
    if isinstance(node, dict):
        for kind in ("Column", "Measure"):
            if kind in node:
                ref = node[kind]
                yield kind.lower(), ref["Expression"]["SourceRef"]["Entity"], ref["Property"]
        for value in node.values():
            yield from visual_fields(value)
    elif isinstance(node, list):
        for value in node:
            yield from visual_fields(value)


def test_visuals_only_use_existing_fields():
    known = {kind: model_fields(kind) for kind in ("column", "measure")}
    visuals = list(REPORT.glob("pages/*/visuals/*/visual.json"))
    assert visuals
    for path in visuals:
        for kind, table, name in visual_fields(json.loads(read(path))):
            assert (table, name) in known[kind], f"{path.parent.name}: {table}[{name}]"


def test_page_order_matches_page_folders():
    pages = json.loads(read(REPORT / "pages" / "pages.json"))
    folders = {p.parent.name for p in REPORT.glob("pages/*/page.json")}
    assert set(pages["pageOrder"]) == folders
    assert pages["activePageName"] in folders


def test_query_groups_are_declared():
    """Power BI cannot open a model that references an undeclared query group."""
    declared = set(re.findall(rf"^queryGroup {NAME}", read(MODEL / "model.tmdl"), re.M))
    used = set()
    for path in MODEL.rglob("*.tmdl"):
        used |= set(re.findall(rf"^\t+queryGroup: {NAME}", read(path), re.M))
    assert used <= declared, used - declared


def squash(text):
    return re.sub(r"\s+", "", text)


def test_fallback_dax_matches_model():
    in_model = {}
    for path in (MODEL / "tables").glob("*.tmdl"):
        for name, dax in re.findall(
            r"^\tmeasure ('[^']+'|\S+) =(.*?)(?=^\t\t(?:formatString|displayFolder):)",
            read(path),
            re.M | re.S,
        ):
            in_model[name.strip("'")] = squash(dax)
    fallback = {}
    for block in read(PBI / "fallback" / "DAX_measures.dax").strip().split("\n\n"):
        _folder, first, *rest = block.split("\n")
        fallback[first.removesuffix(" =")] = squash("".join(rest))
    assert in_model
    assert fallback == in_model


def test_fallback_queries_match_model():
    fallback = squash(read(PBI / "fallback" / "PowerQuery_queries.m"))
    for path in (MODEL / "tables").glob("*.tmdl"):
        source = read(path).split("source =", 1)[1]
        source = source.split("\n\tannotation", 1)[0]
        assert squash(source) in fallback, path.stem


def test_typed_columns_exist_in_data():
    """Every column Power Query types must be present in the CSV it loads."""
    for path in (MODEL / "tables").glob("*.tmdl"):
        text = read(path)
        loaded = re.search(r'GetCsv\("([^"]+)"\)', text)
        if not loaded:
            continue
        header = set(pd.read_csv(ROOT / "data" / "processed" / loaded.group(1), nrows=0).columns)
        typed = set(re.findall(r'\{"([^"]+)", (?:type \w+|Int64\.Type)\}', text))
        assert typed == header, path.stem


def test_tables_do_not_hide_fields():
    """If only some fields of a table are marked "active", Power BI hides the others."""
    for path in REPORT.glob("pages/*/visuals/*/visual.json"):
        visual = json.loads(read(path))["visual"]
        if visual["visualType"] != "tableEx":
            continue
        for role in visual["query"]["queryState"].values():
            flags = {projection.get("active", False) for projection in role["projections"]}
            assert len(flags) == 1, path.parent.name
