import pytest

from lark_cli_mcp.policy import Policy

P = Policy()


@pytest.mark.parametrize("args", [
    ["--version"],
    ["docs", "--help"],
    ["docs", "+create", "--as", "user", "--doc-format", "markdown", "--content", "-"],
    ["drive", "+member-add", "--token", "x"],
    ["auth", "status"],
    ["api", "GET", "/open-apis/contact/v3/users/me"],
    ["docs", "+create", "--content", "email me at a@b.c"],
])
def test_allowed(args):
    assert P.refuse(args) is None


@pytest.mark.parametrize("args, reason", [
    ([], "empty"),
    (["config", "show"], "operator"),
    (["update"], "operator"),
    (["im", "+messages-send"], "domain 'im'"),
    (["auth", "login"], "auth"),
    (["auth"], "auth"),
    (["api", "POST", "/x"], "GET-only"),
    (["api"], "GET-only"),
    (["drive", "+member-remove", "--yes"], "--yes"),
    (["drive", "+member-remove", "--yes=true"], "--yes"),
    (["docs", "+create", "--content", "@/etc/passwd"], "@file"),
    (["docs", "+create", "--content=@notes.md"], "@file"),
    (["docs", "x\x00y"], "NUL"),
])
def test_refused(args, reason):
    why = P.refuse(args)
    assert why is not None and reason in why


def test_env_overrides():
    p = Policy.from_env({
        "LARK_CLI_ALLOWED_DOMAINS": "im, docs",
        "LARK_CLI_ALLOW_YES": "true",
        "LARK_CLI_ALLOW_API_WRITE": "1",
    })
    assert p.refuse(["im", "+messages-send"]) is None
    assert p.refuse(["drive", "--help"]) is not None
    assert p.refuse(["docs", "x", "--yes"]) is None
    assert p.refuse(["api", "POST", "/x"]) is not None  # api not in the domain list


def test_wildcard_domains_keep_operator_commands_out():
    p = Policy.from_env({"LARK_CLI_ALLOWED_DOMAINS": "*"})
    assert p.refuse(["im", "+messages-send"]) is None
    assert p.refuse(["calendar", "+agenda"]) is None
    for head in ("config", "profile", "update"):
        assert "operator" in p.refuse([head, "show"])
    assert "login" in p.refuse(["auth", "login"])
    assert p.refuse(["docs", "x", "--yes"]) is not None
    assert p.refuse(["docs", "--content", "@/data/x"]) is not None


def test_operator_commands_refused_even_when_listed():
    p = Policy.from_env({"LARK_CLI_ALLOWED_DOMAINS": "config,profile,update,docs"})
    for head in ("config", "profile", "update"):
        assert "operator" in p.refuse([head, "show"])
