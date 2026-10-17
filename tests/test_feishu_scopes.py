import importlib.util
import json
from pathlib import Path

import pytest

DIR = Path(__file__).resolve().parent.parent / "feishu-scopes"
spec = importlib.util.spec_from_file_location("make_template", DIR / "make_template.py")
mt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mt)

DOCS = "docs,drive,markdown,wiki,sheets,base,slides,contact".split(",")


@pytest.mark.parametrize("name, domains, no_delete", [
    ("docs-no-delete.json", DOCS, True),
    ("docs-full.json", DOCS, False),
    ("all-no-delete.json", ["all"], True),
    ("all.json", ["all"], False),
])
def test_prebuilt_templates_match_generator(name, domains, no_delete):
    assert json.loads((DIR / name).read_text(encoding="utf-8")) == mt.build(domains, no_delete)


def test_no_delete_drops_delete_scopes():
    user = mt.build(["drive", "base"], no_delete=True)["scopes"]["user"]
    assert "space:document:delete" not in user and "base:record:delete" not in user
    assert "base:record:create" in user and "offline_access" in user


def test_unknown_domain_fails():
    with pytest.raises(SystemExit):
        mt.build(["nope"])
