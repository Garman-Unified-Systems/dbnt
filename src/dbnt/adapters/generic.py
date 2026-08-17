"""Generic adapter - file-based, works anywhere."""

from pathlib import Path

from dbnt.adapters.base import BaseAdapter
from dbnt.core import Rule, RuleType
from dbnt.state import resolve_state_root


class GenericAdapter(BaseAdapter):
    """
    Generic file-based adapter.

    Works with any system that can read markdown files.
    Stores rules in ~/.dbnt/rules/ by default.
    """

    def __init__(self, base_path: Path | None = None):
        self.base_path = resolve_state_root(base_path)
        self.rules_dir = self.base_path / "rules"
        self.successes_dir = self.rules_dir / "successes"
        self.failures_dir = self.rules_dir / "failures"

    def install(self) -> None:
        """Create directory structure."""
        self.successes_dir.mkdir(parents=True, exist_ok=True)
        self.failures_dir.mkdir(parents=True, exist_ok=True)
        print(f"DBNT initialized at {self.base_path}")

    def uninstall(self) -> None:
        """Nothing to uninstall for generic adapter."""
        print("Generic adapter has no system integration to remove")
        print(f"Rules remain at {self.rules_dir}")

    def get_rules_path(self) -> Path:
        """Get rules directory."""
        return self.rules_dir

    def sync_rule(self, rule: Rule) -> None:
        """Save rule to appropriate directory."""
        if rule.type == RuleType.SUCCESS:
            path = self.successes_dir / f"{rule.category.value}-{rule.id}.md"
        else:
            path = self.failures_dir / f"{rule.category.value}-{rule.id}.md"

        path.write_text(rule.to_markdown())

    def is_installed(self) -> bool:
        """Check if directories exist."""
        return self.rules_dir.exists()
