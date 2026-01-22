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


# ============================================================================
# BLUEPRINT ARCHITECTURE MAPPING
# Maps success criteria component names to their blueprint architecture equivalents
# This enables semantic matching between different naming conventions
# ============================================================================

BLUEPRINT_COMPONENT_ALIASES = {
    # Flashpoint / Fusion Layer components
    "flashpointevent": ["flashpoint detector", "flashpoint", "fusion layer", "timeline_event kind=flashpoint"],
    "flashpoint_event": ["flashpoint detector", "flashpoint", "fusion layer"],
    "flashpointdetector": ["flashpoint detector", "flashpoint", "fusion layer"],

    # Dominance / Alert components
    "dominancealert": ["dominance_analyzer", "dominance alerts", "dominance", "50% threshold"],
    "dominance_alert": ["dominance_analyzer", "dominance alerts", "dominance"],
    "livealerts": ["dominance alerts", "alert", "severity indicators", "alert notifications"],
    "live_alerts": ["dominance alerts", "alert", "severity indicators"],
    "severityindicators": ["severity indicators", "color-coded severity", "alert"],

    # Post-Meeting / Summary components
    "summarydocument": ["post-meeting summary", "summary", "narrative", "event_references"],
    "summary_document": ["post-meeting summary", "summary", "narrative"],
    "postmeetingsummary": ["post-meeting summary", "summary", "post meeting"],
    "post_meeting_summary": ["post-meeting summary", "summary"],
    "insightsreport": ["insights report", "insights", "behavioral patterns", "notable moments", "PLAT-F11-C02"],
    "insights_report": ["insights report", "insights", "behavioral patterns"],
    "actionitems": ["action items", "task", "owner", "due_date"],
    "action_items": ["action items", "task", "owner"],
    "decisionlog": ["decisions", "decision log", "statement", "maker", "context"],
    "decision_log": ["decisions", "decision log"],

    # Psychometric / Profile components
    "profileoverlay": ["profile overlay engine", "psychometric profile", "profile context", "PSYC-F04"],
    "profile_overlay": ["profile overlay engine", "psychometric profile", "profile"],
    "psychometricprofile": ["psychometric profile", "profile store", "profile db", "PSYC-F04"],
    "psychometric_profile": ["psychometric profile", "profile store"],
    "assessmentimport": ["assessment import", "import pipeline", "DISC", "MBTI", "Big5"],
    "assessment_import": ["assessment import", "import pipeline"],

    # Nudge components
    "nudgetiming": ["nudge", "timing", "pause points", "speech state"],
    "nudge_timing": ["nudge", "timing", "pause"],
    "nudgecooldown": ["cooldown", "20 sec cooldown", "alert fatigue"],
    "nudge_cooldown": ["cooldown", "20 sec"],
    "reframingsuggestions": ["reframing suggestions", "reframes_per_event", "recommendations"],
    "reframing_suggestions": ["reframing suggestions", "reframes"],

    # Data ingestion components
    "datasetfetcher": ["dataset", "fetcher", "download", "github"],
    "dataset_fetcher": ["dataset", "fetcher", "download"],
    "dataparser": ["parser", "schema", "transform", "extract"],
    "data_parser": ["parser", "schema", "transform"],
    "schemavalidator": ["validator", "validation", "schema", "malformed"],
    "schema_validator": ["validator", "validation"],
    "ingestionpipeline": ["ingestion", "pipeline", "bulk insert", "batch"],
    "ingestion_pipeline": ["ingestion", "pipeline", "bulk"],
    "audittrail": ["audit", "log", "track", "metadata"],
    "audit_trail": ["audit", "log", "track"],
    "rollbackcapability": ["rollback", "transaction", "savepoint"],
    "rollback_capability": ["rollback", "transaction"],
}

# Components intentionally out of MVP scope - don't warn about missing architecture
OUT_OF_MVP_SCOPE = {
    "assessmentimport",
    "assessment_import",
    "actionitems",
    "action_items",
}

# Additional aliases (Hume / Emotion components)
BLUEPRINT_COMPONENT_ALIASES.update({
    "humeaudio": ["hume_audio", "audio_tension", "prosody", "hume"],
    "hume_audio": ["hume_audio", "audio_tension", "prosody"],
    "humeface": ["hume_face", "face_distress", "facial", "hume"],
    "hume_face": ["hume_face", "face_distress", "facial"],

    # Core detection components
    "toneshift": ["tone shift", "tone_shift_detector", "tone"],
    "tone_shift": ["tone shift", "tone_shift_detector"],
    "interruptiondetector": ["interruption", "interrupt", "speaking turns"],
    "interruption_detector": ["interruption", "interrupt"],
    "safetycore": ["safety score", "safety_core", "fatigue"],
    "safety_core": ["safety score", "safety_core"],
})

# Reverse mapping: blueprint terms -> canonical names
BLUEPRINT_TERM_TO_CANONICAL = {}
for canonical, aliases in BLUEPRINT_COMPONENT_ALIASES.items():
    for alias in aliases:
        alias_key = alias.lower().replace(" ", "").replace("_", "").replace("-", "")
        if alias_key not in BLUEPRINT_TERM_TO_CANONICAL:
            BLUEPRINT_TERM_TO_CANONICAL[alias_key] = canonical


def normalize_component_name(name: str) -> str:
    """Normalize a component name for comparison."""
    return name.lower().replace(" ", "").replace("_", "").replace("-", "")


def find_blueprint_aliases(component: str) -> List[str]:
    """Find all blueprint aliases for a component name."""
    normalized = normalize_component_name(component)

    # Direct lookup
    if normalized in BLUEPRINT_COMPONENT_ALIASES:
        return BLUEPRINT_COMPONENT_ALIASES[normalized]

    # Partial match
    for key, aliases in BLUEPRINT_COMPONENT_ALIASES.items():
        if normalized in key or key in normalized:
            return aliases

    return []


def component_matches_blueprint(component: str, blueprint_text: str) -> bool:
    """Check if a component matches blueprint text using aliases."""
    blueprint_lower = blueprint_text.lower()

    # Direct match
    if normalize_component_name(component) in normalize_component_name(blueprint_text):
        return True

    # Alias match
    aliases = find_blueprint_aliases(component)
    for alias in aliases:
        if alias.lower() in blueprint_lower:
            return True

    return False


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

# IMPORTANT PRINCIPLE: Components must NOT CONTRADICT the blueprint.
# - Contradictions (FAIL): Component violates existing architecture
# - Gaps (PASS): Component not yet documented but doesn't conflict
# - Aligned (PASS): Component explicitly documented in blueprint
#
# Gaps are acceptable - contradictions are not.
# See: component_to_blueprint_mapping.csv for explicit mapping

def compare_task_to_blueprint(task: str, architecture: BlueprintContext) -> CheckResult:
    """
    Compare task against architectural constraints from Blueprint diagrams.

    IMPORTANT: The goal is to detect CONTRADICTIONS, not just gaps.
    - A component not in blueprint = gap (acceptable)
    - A component that violates blueprint patterns = contradiction (fail)

    Uses semantic alias matching to recognize equivalent component names
    (e.g., "FlashpointEvent" matches "Flashpoint Detector" in blueprints).

    Returns:
    - PASS: Task fits within architecture (aligned or gap with no conflict)
    - FAIL: Task violates/contradicts architectural patterns
    - MISSING: No relevant architecture found
    """
    result = CheckResult(source="Blueprint")

    if not architecture.diagrams:
        result.add_missing("No relevant architecture diagrams found")
        return result

    task_components = extract_components_from_task(task)
    keywords = extract_keywords(task)

    # Collect all blueprint text for semantic matching
    all_blueprint_text = ""
    for diagram in architecture.diagrams:
        result.add_match(
            f"Related diagram: {diagram.filename}",
            {"components": diagram.components, "flows": diagram.flows}
        )
        all_blueprint_text += " " + diagram.content

    for component in task_components:
        component_lower = component.lower()
        found = False
        matched_via_alias = False

        # First try direct match in architecture components
        for arch_component in architecture.components:
            if component_lower in arch_component.lower():
                diagram = architecture.get_diagram(arch_component)
                result.add_match(f"Component '{component}' found in {diagram}")
                found = True
                break

        # If not found, try semantic alias matching against full blueprint content
        if not found:
            if component_matches_blueprint(component, all_blueprint_text):
                aliases = find_blueprint_aliases(component)
                matched_alias = next((a for a in aliases if a.lower() in all_blueprint_text.lower()), None)
                if matched_alias:
                    result.add_match(
                        f"Component '{component}' → blueprint '{matched_alias}' (semantic match)"
                    )
                    found = True
                    matched_via_alias = True

        # If still not found, check if any alias exists in blueprint
        if not found:
            aliases = find_blueprint_aliases(component)
            for alias in aliases:
                for diagram in architecture.diagrams:
                    if alias.lower() in diagram.content.lower():
                        result.add_match(
                            f"Component '{component}' → '{alias}' in {diagram.filename}"
                        )
                        found = True
                        matched_via_alias = True
                        break
                if found:
                    break

        if not found:
            # Check if component is out of MVP scope (don't warn)
            normalized = normalize_component_name(component)
            if normalized in OUT_OF_MVP_SCOPE:
                result.add_match(f"Component '{component}' - out of MVP scope (no architecture needed)")
                continue

            # Gap (not documented) is OK - only contradictions would fail
            # Mark as gap but don't warn - gaps are acceptable per ALIGNMENT_PRINCIPLES.md
            result.add_match(f"Component '{component}' - gap (not yet documented, no contradiction)")

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
