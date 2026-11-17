"""Base adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar

from dbnt.agency import enforce_action

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from dbnt.agency import ActionProposal
    from dbnt.core import Rule

T = TypeVar("T")


class BaseAdapter(ABC):
    """Base class for DBNT adapters."""

    def run_action(self, proposal: ActionProposal, action: Callable[[], T]) -> T:
        """Execute a callback only after the bounded-agency policy returns MOVE."""

        enforce_action(proposal)
        return action()

    @abstractmethod
    def install(self) -> None:
        """Install DBNT into the target system."""
        pass

    @abstractmethod
    def uninstall(self) -> None:
        """Remove DBNT from the target system."""
        pass

    @abstractmethod
    def get_rules_path(self) -> Path:
        """Get the path where rules should be stored."""
        pass

    @abstractmethod
    def sync_rule(self, rule: Rule) -> None:
        """Sync a rule to the target system's format."""
        pass

    @abstractmethod
    def is_installed(self) -> bool:
        """Check if DBNT is installed in the target system."""
        pass
