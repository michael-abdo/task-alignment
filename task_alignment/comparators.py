"""Comparison functions for Task Alignment System.

Each comparator checks a task against one source of truth and returns a CheckResult.
"""

from __future__ import annotations

import re
from typing import List

from .models import (
    CheckResult,
    BlueprintContext,
    CodebaseContext,
    RoadmapContext,
    RequirementsContext,
)
from .fetchers import extract_keywords


def extract_components_from_task(task: str) -> List[str]:
    """Extract component names mentioned in a task."""
    patterns = [
        r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b',
        r'\b([a-z]+_[a-z_]+)\b',
        r'component[:\s]+([A-Za-z_]+)',
        r'service[:\s]+([A-Za-z_]+)',
        r'module[:\s]+([A-Za-z_]+)',
    ]

    components = []
    for pattern in patterns:
        components.extend(re.findall(pattern, task))

    return list(set(components))


def extract_data_flows_from_task(task: str) -> List[str]:
    """Extract data flow descriptions from a task."""
    flow_indicators = [
        r'(\w+)\s+(?:to|->|→)\s+(\w+)',
        r'from\s+(\w+)\s+to\s+(\w+)',
        r'(\w+)\s+(?:sends?|emit|publish)\s+.*?(?:to|into)\s+(\w+)',
    ]

    flows = []
    for pattern in flow_indicators:
        for match in re.finditer(pattern, task, re.IGNORECASE):
            flows.append(f"{match.group(1)} -> {match.group(2)}")

    return flows


def extract_dependencies_from_task(task: str) -> List[str]:
    """Extract potential dependencies mentioned in a task."""
    common_deps = [
        "numpy", "pandas", "flask", "fastapi", "django", "sqlalchemy",
        "redis", "kafka", "postgresql", "mongodb", "react", "next",
        "typescript", "tailwind", "websocket", "anthropic", "openai",
        "hume", "zoom", "rtms", "claude",
    ]

    task_lower = task.lower()
    return [dep for dep in common_deps if dep in task_lower]


# ============================================================================
# BLUEPRINT COMPARATOR
# ============================================================================

def compare_task_to_blueprint(task: str, architecture: BlueprintContext) -> CheckResult:
    """
    Compare task against architectural constraints from Blueprint diagrams.

    Returns:
    - PASS: Task fits within architecture
    - FAIL: Task violates architectural patterns
    - MISSING: No relevant architecture found
    """
    result = CheckResult(source="Blueprint")

    if not architecture.diagrams:
        result.add_missing("No relevant architecture diagrams found")
        return result

    task_components = extract_components_from_task(task)
    keywords = extract_keywords(task)

    for diagram in architecture.diagrams:
        result.add_match(
            f"Related diagram: {diagram.filename}",
            {"components": diagram.components, "flows": diagram.flows}
        )

    for component in task_components:
        component_lower = component.lower()
        found = False

        for arch_component in architecture.components:
            if component_lower in arch_component.lower():
                diagram = architecture.get_diagram(arch_component)
                result.add_match(f"Component '{component}' found in {diagram}")
                found = True
                break

        if not found:
            result.add_warning(f"Component '{component}' not explicitly in architecture")

    task_flows = extract_data_flows_from_task(task)
    for flow in task_flows:
        if architecture.validates_flow(flow):
            result.add_match(f"Data flow '{flow}' supported by architecture")
        else:
            if architecture.data_flows:
                result.add_warning(f"Data flow '{flow}' not explicitly documented")

    all_components = " ".join(architecture.components.keys()).lower()
    for keyword in keywords:
        if keyword in all_components:
            result.add_match(f"Keyword '{keyword}' relates to architecture")

    return result


# ============================================================================
# CODEBASE COMPARATOR
# ============================================================================

def compare_task_to_codebase(task: str, code: CodebaseContext) -> CheckResult:
    """
    Compare task against existing codebase.

    Checks:
    - Does similar functionality already exist?
    - Are dependencies available?
    - Does task align with current code patterns?
    """
    result = CheckResult(source="Codebase")

    if not code.files:
        result.add_missing("No relevant code files found in codebase")
        return result

    for file in code.files[:5]:
        result.add_match(f"Related file: {file.path}")

        if file.functions:
            result.raw_data[file.path] = {
                "functions": file.functions[:10],
                "classes": file.classes[:10],
            }

    if code.existing_implementations:
        for impl in code.existing_implementations[:5]:
            result.add_warning(f"Similar implementation exists: {impl}")
        result.add_warning("Consider refactoring existing code rather than creating new")

    required_deps = extract_dependencies_from_task(task)
    for dep in required_deps:
        if dep in code.available_dependencies:
            result.add_match(f"Dependency '{dep}' is available")
        else:
            result.add_missing(f"Dependency '{dep}' may need to be installed")

    if code.files:
        file_types = set(f.language for f in code.files)
        if "python" in file_types and "python" not in task.lower():
            result.add_match("Codebase uses Python - task appears compatible")
        if "typescript" in file_types and any(
            kw in task.lower() for kw in ["frontend", "ui", "component", "react"]
        ):
            result.add_match("Codebase uses TypeScript - frontend task compatible")

    return result


# ============================================================================
# ROADMAP COMPARATOR
# ============================================================================

def compare_task_to_roadmap(task: str, roadmap: RoadmapContext) -> CheckResult:
    """
    Compare task against roadmap and Monday.com.

    Checks:
    - Is task in the roadmap?
    - Is it prioritized for current sprint?
    - Are dependencies tracked?
    """
    result = CheckResult(source="Roadmap")

    if roadmap.matches:
        for match in roadmap.matches:
            result.add_match(
                f"Found in roadmap: {match.feature_id} | {match.component_id} - {match.component_name}"
            )
            if match.status:
                result.add_match(f"Status: {match.status}")
            if match.owner:
                result.add_match(f"Owner: {match.owner}")
    else:
        result.add_missing("Task not found in roadmap - may need to be added")

    if roadmap.monday_items:
        error_items = [i for i in roadmap.monday_items if "error" in i]
        if error_items:
            result.add_warning(f"Monday.com: {error_items[0].get('error')}")
        else:
            for item in roadmap.monday_items[:3]:
                result.add_match(
                    f"Monday.com item: {item.get('name')} ({item.get('board')})"
                )

    if roadmap.is_in_current_sprint(task):
        result.add_match("Task is in current sprint")
    else:
        if roadmap.matches:
            result.add_warning("Task found but not in current sprint")

    if roadmap.features:
        for feature_name, feature_data in list(roadmap.features.items())[:3]:
            result.add_match(f"Feature match: {feature_name[:80]}...")

    return result


# ============================================================================
# REQUIREMENTS COMPARATOR
# ============================================================================

def compare_task_to_requirements(task: str, requirements: RequirementsContext) -> CheckResult:
    """
    Compare task against Greg's requirements.

    Checks:
    - Are acceptance criteria defined?
    - Does task match business requirements?
    - Are estimates available?
    """
    result = CheckResult(source="Requirements")

    if requirements.acceptance_criteria:
        for criteria in requirements.acceptance_criteria[:3]:
            result.add_match(f"Acceptance criteria: {criteria[:100]}...")
    else:
        result.add_missing("No acceptance criteria defined for this task")

    if requirements.success_criteria:
        for criteria in requirements.success_criteria[:3]:
            result.add_match(f"Success criteria: {criteria[:100]}...")

    if requirements.estimated_hours:
        result.add_match(f"Estimated hours: {requirements.estimated_hours}")

    if requirements.estimated_loc:
        result.add_match(f"Estimated LOC: ~{requirements.estimated_loc}")

    if requirements.requirement_files:
        for filename in list(requirements.requirement_files.keys())[:3]:
            result.add_match(f"Requirement file: {filename}")

    if not requirements.requirement_files and not requirements.acceptance_criteria:
        result.add_missing("No requirement files found matching this task")

    return result


# ============================================================================
# CROSS-SOURCE COHERENCE
# ============================================================================

def check_cross_source_coherence(
    blueprint: BlueprintContext,
    codebase: CodebaseContext,
    roadmap: RoadmapContext,
    requirements: RequirementsContext
) -> CheckResult:
    """
    Check coherence across all sources of truth.

    Verifies:
    - All sources agree on scope
    - No conflicting definitions
    - Naming is consistent across sources
    """
    result = CheckResult(source="Cross-Source Coherence")

    sources_with_data = 0
    if blueprint.diagrams:
        sources_with_data += 1
    if codebase.files:
        sources_with_data += 1
    if roadmap.matches or roadmap.monday_items:
        sources_with_data += 1
    if requirements.acceptance_criteria or requirements.requirement_files:
        sources_with_data += 1

    result.add_match(f"Data found in {sources_with_data}/4 sources")

    if sources_with_data < 2:
        result.add_warning("Limited cross-source validation possible")

    blueprint_components = set(
        c.lower() for c in blueprint.components.keys()
    )
    code_symbols = set()
    for f in codebase.files:
        code_symbols.update(fn.lower() for fn in f.functions)
        code_symbols.update(cls.lower() for cls in f.classes)

    if blueprint_components and code_symbols:
        overlap = blueprint_components & code_symbols
        if overlap:
            result.add_match(f"Naming consistent: {', '.join(list(overlap)[:5])}")
        else:
            result.add_warning("No direct naming overlap between blueprint and code")

    if roadmap.matches and requirements.acceptance_criteria:
        result.add_match("Both roadmap entry and requirements found - good traceability")
    elif roadmap.matches and not requirements.acceptance_criteria:
        result.add_warning("In roadmap but missing acceptance criteria")
    elif requirements.acceptance_criteria and not roadmap.matches:
        result.add_warning("Has requirements but not tracked in roadmap")

    return result
