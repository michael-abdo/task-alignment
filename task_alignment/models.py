"""Data models for Task Alignment System."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class AlignmentStatus(Enum):
    """Overall alignment status."""
    ALIGNED = "aligned"
    CONFLICTS = "conflicts"
    MISSING_INFO = "missing_info"

    @property
    def emoji(self) -> str:
        return {
            AlignmentStatus.ALIGNED: "✓",
            AlignmentStatus.CONFLICTS: "⚠",
            AlignmentStatus.MISSING_INFO: "?"
        }[self]


class CheckStatus(Enum):
    """Status for individual checks."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    MISSING = "missing"

    @property
    def emoji(self) -> str:
        return {
            CheckStatus.PASS: "✓",
            CheckStatus.WARNING: "⚠",
            CheckStatus.FAIL: "✗",
            CheckStatus.MISSING: "?"
        }[self]


@dataclass
class CheckResult:
    """Result of checking task against one source of truth."""
    source: str  # "Blueprint", "Codebase", "Roadmap", "Requirements"
    status: CheckStatus = CheckStatus.MISSING
    matches: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def add_match(self, item: str, details: Any = None) -> None:
        self.matches.append(item)
        if details:
            self.raw_data[f"match_{len(self.matches)}"] = details

    def add_conflict(self, item: str) -> None:
        self.conflicts.append(item)

    def add_missing(self, item: str) -> None:
        self.missing.append(item)

    def add_warning(self, item: str) -> None:
        self.warnings.append(item)

    def compute_status(self) -> CheckStatus:
        if self.conflicts:
            self.status = CheckStatus.FAIL
        elif self.missing and not self.matches:
            self.status = CheckStatus.MISSING
        elif self.warnings:
            self.status = CheckStatus.WARNING
        else:
            self.status = CheckStatus.PASS
        return self.status

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "status": self.status.value,
            "matches": self.matches,
            "conflicts": self.conflicts,
            "missing": self.missing,
            "warnings": self.warnings,
        }


@dataclass
class AlignmentReport:
    """Final report returned by check_task_alignment()."""
    task: str
    checks: List[CheckResult] = field(default_factory=list)
    overall_status: AlignmentStatus = AlignmentStatus.MISSING_INFO
    created_at: datetime = field(default_factory=datetime.now)

    def add_check(self, check: CheckResult) -> None:
        check.compute_status()
        self.checks.append(check)

    def compute_overall_status(self) -> AlignmentStatus:
        has_conflicts = any(c.status == CheckStatus.FAIL for c in self.checks)
        has_missing = any(c.status == CheckStatus.MISSING for c in self.checks)

        if has_conflicts:
            self.overall_status = AlignmentStatus.CONFLICTS
        elif has_missing:
            self.overall_status = AlignmentStatus.MISSING_INFO
        else:
            self.overall_status = AlignmentStatus.ALIGNED

        return self.overall_status

    def to_markdown(self) -> str:
        md = f"# Alignment Report: {self.task}\n\n"
        md += f"**Overall Status:** {self.overall_status.emoji} {self.overall_status.value.upper()}\n\n"
        md += f"*Generated: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"

        for check in self.checks:
            md += f"## {check.source}\n"
            md += f"**Status:** {check.status.emoji} {check.status.value.upper()}\n\n"

            if check.matches:
                md += "**Matches:**\n"
                for item in check.matches:
                    md += f"- {item}\n"
                md += "\n"

            if check.conflicts:
                md += "**Conflicts:**\n"
                for item in check.conflicts:
                    md += f"- ✗ {item}\n"
                md += "\n"

            if check.missing:
                md += "**Missing:**\n"
                for item in check.missing:
                    md += f"- ? {item}\n"
                md += "\n"

            if check.warnings:
                md += "**Warnings:**\n"
                for item in check.warnings:
                    md += f"- ⚠ {item}\n"
                md += "\n"

        return md

    def to_dict(self) -> Dict:
        return {
            "task": self.task,
            "overall_status": self.overall_status.value,
            "created_at": self.created_at.isoformat(),
            "checks": [c.to_dict() for c in self.checks],
        }


# ============================================================================
# Context Classes - Hold data from each source of truth
# ============================================================================

@dataclass
class DiagramInfo:
    """Information about a Mermaid diagram."""
    filename: str
    path: str
    content: str
    components: List[str] = field(default_factory=list)
    flows: List[str] = field(default_factory=list)


@dataclass
class BlueprintContext:
    """Context from architecture blueprints (Mike's Mermaid diagrams)."""
    diagrams: List[DiagramInfo] = field(default_factory=list)
    components: Dict[str, str] = field(default_factory=dict)
    data_flows: List[str] = field(default_factory=list)

    def add_diagram(self, diagram: DiagramInfo) -> None:
        self.diagrams.append(diagram)
        self.components.update({c: diagram.filename for c in diagram.components})
        self.data_flows.extend(diagram.flows)

    def get_diagram(self, component: str) -> Optional[str]:
        return self.components.get(component)

    def validates_flow(self, flow: str) -> bool:
        flow_lower = flow.lower()
        return any(flow_lower in f.lower() for f in self.data_flows)


@dataclass
class CodeFile:
    """Information about a code file."""
    path: str
    content: str
    language: str = "python"
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)


@dataclass
class CodebaseContext:
    """Context from GitHub codebase (Youssef/Patrick)."""
    files: List[CodeFile] = field(default_factory=list)
    existing_implementations: List[str] = field(default_factory=list)
    available_dependencies: List[str] = field(default_factory=list)

    def add_file(self, path: str, content: str) -> None:
        self.files.append(CodeFile(path=path, content=content))


@dataclass
class RoadmapMatch:
    """A matching item from the roadmap."""
    feature_id: str
    component_id: str
    component_name: str
    status: str
    priority: str = ""
    owner: str = ""


@dataclass
class RoadmapContext:
    """Context from Roadmap and Monday.com (Shanti)."""
    monday_items: List[Dict] = field(default_factory=list)
    features: Dict[str, Any] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)
    matches: List[RoadmapMatch] = field(default_factory=list)
    current_sprint_items: List[str] = field(default_factory=list)

    def add_monday_items(self, items: List[Dict]) -> None:
        self.monday_items.extend(items)

    def is_in_current_sprint(self, task: str) -> bool:
        task_lower = task.lower()
        return any(task_lower in item.lower() for item in self.current_sprint_items)


@dataclass
class RequirementsContext:
    """Context from Greg's requirements (email attachments)."""
    requirement_files: Dict[str, str] = field(default_factory=dict)
    acceptance_criteria: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    estimated_hours: Optional[float] = None
    estimated_loc: Optional[int] = None

    def add_requirement_file(self, filename: str, content: str) -> None:
        self.requirement_files[filename] = content
