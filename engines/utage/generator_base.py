"""Utage-specific sentence generator base contract."""

from typing import Any, Dict, List, Optional

from core.dict_based_sentence_generator import DictBasedSentenceGenerator
from core.scenario_state.effects import VisualStateEffect


UtageCommand = Dict[str, Any]


class UtageGeneratorBase(DictBasedSentenceGenerator):
    """Shared output helpers and extension points for Utage generators."""

    def create_command(self, command: str = "") -> UtageCommand:
        """Create one Utage output row."""
        return self.create_command_dict(command)

    def set_param(
        self,
        line: UtageCommand,
        param_name: str,
        data: Dict[str, Any],
        field_name: Optional[str] = None,
        use_default: bool = False,
    ) -> None:
        """Write a configured parameter while preserving current output behavior."""
        self._set_param_fast(
            line,
            param_name,
            data,
            field_name=field_name,
            use_default=use_default,
        )

    def set_wait_type(self, line: UtageCommand, data: Dict[str, Any]) -> None:
        """Copy the shared Utage wait mode, including receive-all generators."""
        if "WaitType" in data:
            self.set_param(line, "WaitType", data, field_name="WaitType")

    def state_effects(
        self,
        data: Dict[str, Any],
        context: Optional[Any] = None,
    ) -> List[VisualStateEffect]:
        """Return state changes caused by this row; stateless generators return none."""
        return []
