"""Registry of the guided workshop missions (content lives in ``missions/*.md``)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend import config


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
    Mission("1", "Mission 1 — Data Detective: Where Does the ISS Data Come From?", 15, "mission-1.md"),
    Mission("2", "Mission 2 — Orbit Explorer: How Does OrbitX Track the ISS?", 15, "mission-2.md"),
    Mission("3", "Mission 3 — Mission Upgrade: Find the Flaws. Build What's Next.", 10, "mission-3.md"),
)

# Core level-2 headings required across all mission guides (``## <name>``).
REQUIRED_SECTIONS = (
    "Learning objective",
    "Estimated duration",
    "Concept",
    "Deliverable",
)
