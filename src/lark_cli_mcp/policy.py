"""Which lark-cli invocations the MCP tool may run.

The tool never goes through a shell, so this only has to decide which argv
lists are acceptable. Everything here is a refusal rule; anything not refused
is passed to lark-cli unchanged.
"""
from dataclasses import dataclass, field

DEFAULT_DOMAINS = (
    "docs,drive,markdown,wiki,base,sheets,contact,"
    "schema,skills,auth,doctor,api,help,whoami"
)
# CLI management stays with the server operator, whatever the domain list says.
OPERATOR_ONLY = frozenset({"config", "profile", "update"})
# Read-only auth subcommands. login / logout stay with whoever runs the server.
AUTH_READ_ONLY = frozenset({"status", "scopes", "check", "list"})
TOP_LEVEL_INFO = frozenset({"--version", "--help", "-h"})


@dataclass(frozen=True)
class Policy:
    domains: frozenset[str] = field(default_factory=lambda: frozenset(DEFAULT_DOMAINS.split(",")))
    allow_yes: bool = False
    allow_file_args: bool = False
    api_get_only: bool = True

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "Policy":
        def flag(name: str) -> bool:
            return env.get(name, "").strip().lower() in {"1", "true", "yes"}

        domains = env.get("LARK_CLI_ALLOWED_DOMAINS", DEFAULT_DOMAINS)
        return cls(
            domains=frozenset(d.strip() for d in domains.split(",") if d.strip()),
            allow_yes=flag("LARK_CLI_ALLOW_YES"),
            allow_file_args=flag("LARK_CLI_ALLOW_FILE_ARGS"),
            api_get_only=not flag("LARK_CLI_ALLOW_API_WRITE"),
        )

    def refuse(self, args: list[str]) -> str | None:
        """Return why `lark-cli *args` is refused, or None when it may run."""
        if not args:
            return "args is empty"
        if any(not isinstance(a, str) or "\x00" in a for a in args):
            return "every argument must be a string without NUL bytes"
        head = args[0]
        if head in TOP_LEVEL_INFO and len(args) == 1:
            return None
        if head in OPERATOR_ONLY:
            return f"'{head}' is CLI management and is done by the server operator"
        if head not in self.domains and "*" not in self.domains:
            return f"domain '{head}' is not allowed here; allowed: {', '.join(sorted(self.domains))}"
        if head == "auth" and (len(args) < 2 or args[1] not in AUTH_READ_ONLY):
            return "only 'auth " + "/".join(sorted(AUTH_READ_ONLY)) + "' are allowed; login is done by the server operator"
        if head == "api" and self.api_get_only and (len(args) < 2 or args[1].upper() != "GET"):
            return "raw api calls are GET-only here; use a +shortcut or typed command to write"
        for a in args:
            if not self.allow_yes and (a == "--yes" or a.startswith("--yes=")):
                return "--yes (high-risk-write) is refused; ask the operator to run it by hand"
            if not self.allow_file_args and (a.startswith("@") or "=@" in a):
                return "@file arguments are refused; pass content through stdin with '-'"
        return None
