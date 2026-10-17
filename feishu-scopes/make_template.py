"""Build a Feishu Open Platform scope template for "批量导入/导出权限".

    python feishu-scopes/make_template.py --domains docs,drive,wiki --no-delete
    python feishu-scopes/make_template.py --domains all --with-tenant > all.json

Scopes come from domain-scopes.lark-cli-<version>.json next to this file.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "domain-scopes.lark-cli-1.0.98.json"
# lark-cli adds this to every user login so it can refresh the token.
ALWAYS_USER = ("offline_access",)


def is_delete(scope: str) -> bool:
    return "delete" in scope


def build(domains, no_delete=False, with_tenant=False, data=None):
    data = data or json.loads(DATA.read_text(encoding="utf-8"))
    known = data["domains"]
    if domains == ["all"]:
        domains = sorted(known)
    unknown = [d for d in domains if d not in known]
    if unknown:
        raise SystemExit(f"unknown domain(s): {', '.join(unknown)}; known: {', '.join(sorted(known))}")

    def pick(identity):
        scopes = {s for d in domains for s in known[d][identity]}
        if no_delete:
            scopes = {s for s in scopes if not is_delete(s)}
        return sorted(scopes)

    user = sorted(set(pick("user")) | set(ALWAYS_USER))
    return {"scopes": {"tenant": pick("tenant") if with_tenant else [], "user": user}}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--domains", required=True, help="comma-separated lark-cli domains, or 'all'")
    p.add_argument("--no-delete", action="store_true", help="leave out every scope whose name contains 'delete'")
    p.add_argument("--with-tenant", action="store_true", help="also fill tenant (app identity) scopes, for --as bot")
    a = p.parse_args(argv)
    domains = [d.strip() for d in a.domains.split(",") if d.strip()]
    json.dump(build(domains, a.no_delete, a.with_tenant), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
