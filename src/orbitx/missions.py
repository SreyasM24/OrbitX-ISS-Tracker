"""Registry of the guided workshop missions (content lives in ``missions/*.md``)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from orbitx import config


@dataclass(frozen=True)
class Mission:
    key: str
    title: str
    minutes: int
    filename: str

    @property
    def path(self) -> Path:
        return config.MISSIONS_DIR / self.filename

    def read(self) -> str:
        """Markdown text, or a short actionable message if the file is missing."""
        try:
            return self.path.read_text(encoding="utf-8")
        except OSError:
            return f"Mission file `missions/{self.filename}` was not found. Re-pull the repository."


MISSIONS: tuple[Mission, ...] = (
    Mission("1", "Mission 1 · Where Is the ISS?", 20, "mission-1.md"),
    Mission("2", "Mission 2 · Put the ISS on a Map", 20, "mission-2.md"),
    Mission("3", "Mission 3 · Where Will It Be?", 25, "mission-3.md"),
    Mission("4", "Mission 4 · Can We See It?", 15, "mission-4.md"),
    Mission("5", "Final · New City Challenge", 10, "final-challenge.md"),
)

# Every mission file must contain each of these as a level-2 heading (``## <name>``).
REQUIRED_SECTIONS = (
    "Learning objective",
    "Estimated duration",
    "Concept",
    "Source files",
    "Instructions",
    "Your task",
    "AI prompt",
    "Expected outcome",
    "Verify",
    "Common errors",
    "Optional extension",
)
