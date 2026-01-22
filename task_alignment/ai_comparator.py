"""AI-powered semantic comparison using OpenAI API.

Provides intelligent task alignment checking that understands:
- Semantic similarity (not just keyword matching)
- Synonyms and related concepts
- Architectural intent and patterns
- Business requirement alignment
"""

from __future__ import annotations

import os
import json
from typing import Optional
from dataclasses import dataclass

from .models import (
    CheckResult,
    CheckStatus,
    BlueprintContext,
    CodebaseContext,
    RoadmapContext,
    RequirementsContext,
)


@dataclass
class AIConfig:
    """Configuration for OpenAI API."""
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 1000

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.environ.get("OPENAI_API_KEY")


def get_openai_client(config: AIConfig):
    """Get OpenAI client, raising clear error if not available."""
    try:
        from openai import OpenAI
        if not config.api_key:
            raise ValueError("OPENAI_API_KEY not set. Set it in environment or pass to AIConfig.")
        return OpenAI(api_key=config.api_key)
    except ImportError:
        raise ImportError("openai package not installed. Run: pip install openai")


def ai_compare_blueprint(
    task: str,
    context: BlueprintContext,
    config: Optional[AIConfig] = None
) -> CheckResult:
    """
    Use AI to semantically compare task against architecture blueprints.
    """
    config = config or AIConfig()
    result = CheckResult(source="Blueprint (AI)")

    if not context.diagrams:
        result.add_missing("No architecture diagrams found")
        return result

    diagram_summaries = []
    for d in context.diagrams[:5]:
        diagram_summaries.append(f"**{d.filename}**:\nComponents: {', '.join(d.components[:10])}\nFlows: {', '.join(d.flows[:5])}")

    architecture_context = "\n\n".join(diagram_summaries)

    prompt = f"""Analyze whether this task aligns with the existing architecture.

TASK: {task}

ARCHITECTURE DIAGRAMS:
{architecture_context}

Respond in JSON format:
{{
    "alignment": "aligned" | "partial" | "conflict" | "missing",
    "confidence": 0.0-1.0,
    "matching_components": ["list of components this task relates to"],
    "potential_conflicts": ["any architectural concerns"],
    "recommendations": ["suggestions for implementation"],
    "explanation": "brief explanation of alignment assessment"
}}"""

    try:
        client = get_openai_client(config)
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": "You are an expert software architect analyzing task alignment with system architecture."},
                {"role": "user", "content": prompt}
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            response_format={"type": "json_object"}
        )

        analysis = json.loads(response.choices[0].message.content)

        result.raw_data["ai_analysis"] = analysis
        result.raw_data["model"] = config.model

        if analysis.get("alignment") == "aligned":
            result.status = CheckStatus.PASS
            result.add_match(f"AI Assessment: {analysis.get('explanation', 'Task aligns with architecture')}")
        elif analysis.get("alignment") == "partial":
            result.status = CheckStatus.WARNING
            result.add_warning(f"Partial alignment: {analysis.get('explanation')}")
        elif analysis.get("alignment") == "conflict":
            result.status = CheckStatus.FAIL
            result.add_conflict(f"Conflict detected: {analysis.get('explanation')}")
        else:
            result.status = CheckStatus.MISSING
            result.add_missing(f"Insufficient data: {analysis.get('explanation')}")

        for comp in analysis.get("matching_components", []):
            result.add_match(f"Related component: {comp}")

        for conflict in analysis.get("potential_conflicts", []):
            result.add_warning(f"Potential issue: {conflict}")

        for rec in analysis.get("recommendations", []):
            result.add_match(f"Recommendation: {rec}")

    except Exception as e:
        result.add_warning(f"AI analysis failed: {str(e)}")
        result.status = CheckStatus.MISSING

    return result


def ai_compare_codebase(
    task: str,
    context: CodebaseContext,
    config: Optional[AIConfig] = None
) -> CheckResult:
    """
    Use AI to semantically compare task against existing codebase.
    """
    config = config or AIConfig()
    result = CheckResult(source="Codebase (AI)")

    if not context.files:
        result.add_missing("No relevant code files found")
        return result

    code_summaries = []
    for f in context.files[:5]:
        funcs = ", ".join(f.functions[:10]) if f.functions else "none"
        classes = ", ".join(f.classes[:5]) if f.classes else "none"
        code_summaries.append(f"**{f.path}** ({f.language})\n  Functions: {funcs}\n  Classes: {classes}")

    codebase_context = "\n".join(code_summaries)

    existing_impl = "\n".join(context.existing_implementations[:5]) if context.existing_implementations else "None found"

    prompt = f"""Analyze whether this task duplicates existing code or integrates well with the codebase.

TASK: {task}

RELEVANT FILES:
{codebase_context}

POTENTIALLY SIMILAR IMPLEMENTATIONS:
{existing_impl}

Respond in JSON format:
{{
    "assessment": "new_feature" | "refactor_existing" | "duplicate" | "integration",
    "confidence": 0.0-1.0,
    "related_files": ["files that should be modified or referenced"],
    "existing_code_to_reuse": ["functions/classes that could be reused"],
    "potential_conflicts": ["any code conflicts or breaking changes"],
    "implementation_approach": "recommended approach",
    "explanation": "brief explanation"
}}"""

    try:
        client = get_openai_client(config)
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": "You are an expert software engineer analyzing code for potential duplication and integration points."},
                {"role": "user", "content": prompt}
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            response_format={"type": "json_object"}
        )

        analysis = json.loads(response.choices[0].message.content)

        result.raw_data["ai_analysis"] = analysis
        result.raw_data["model"] = config.model

        assessment = analysis.get("assessment", "")

        if assessment == "new_feature":
            result.status = CheckStatus.PASS
            result.add_match(f"New feature: {analysis.get('explanation')}")
        elif assessment == "refactor_existing":
            result.status = CheckStatus.WARNING
            result.add_warning(f"Consider refactoring: {analysis.get('explanation')}")
        elif assessment == "duplicate":
            result.status = CheckStatus.FAIL
            result.add_conflict(f"Potential duplicate: {analysis.get('explanation')}")
        else:
            result.status = CheckStatus.PASS
            result.add_match(f"Integration: {analysis.get('explanation')}")

        for file in analysis.get("related_files", []):
            result.add_match(f"Related file: {file}")

        for reuse in analysis.get("existing_code_to_reuse", []):
            result.add_match(f"Reusable: {reuse}")

        if analysis.get("implementation_approach"):
            result.add_match(f"Approach: {analysis.get('implementation_approach')}")

        for conflict in analysis.get("potential_conflicts", []):
            result.add_warning(f"Potential conflict: {conflict}")

    except Exception as e:
        result.add_warning(f"AI analysis failed: {str(e)}")
        result.status = CheckStatus.MISSING

    return result


def ai_compare_roadmap(
    task: str,
    context: RoadmapContext,
    config: Optional[AIConfig] = None
) -> CheckResult:
    """
    Use AI to semantically compare task against roadmap items.
    """
    config = config or AIConfig()
    result = CheckResult(source="Roadmap (AI)")

    roadmap_items = []

    for match in context.matches[:10]:
        roadmap_items.append(f"- {match.feature_id} | {match.component_name} (Status: {match.status})")

    for item in context.monday_items[:10]:
        if "error" not in item:
            roadmap_items.append(f"- Monday: {item.get('name')} ({item.get('board')}) - {item.get('status')}")

    for feature, data in list(context.features.items())[:5]:
        roadmap_items.append(f"- Feature: {feature[:80]}")

    if not roadmap_items:
        result.add_missing("No roadmap data available")
        return result

    roadmap_context = "\n".join(roadmap_items)

    prompt = f"""Analyze whether this task is tracked in the roadmap and properly prioritized.

TASK: {task}

ROADMAP ITEMS:
{roadmap_context}

Respond in JSON format:
{{
    "tracking_status": "tracked" | "partially_tracked" | "not_tracked",
    "confidence": 0.0-1.0,
    "matching_items": ["roadmap items that match this task"],
    "priority_assessment": "high" | "medium" | "low" | "unknown",
    "dependencies": ["any dependent tasks that should be completed first"],
    "gaps": ["missing roadmap entries or tracking issues"],
    "explanation": "brief explanation"
}}"""

    try:
        client = get_openai_client(config)
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": "You are a project manager analyzing task tracking and roadmap alignment."},
                {"role": "user", "content": prompt}
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            response_format={"type": "json_object"}
        )

        analysis = json.loads(response.choices[0].message.content)

        result.raw_data["ai_analysis"] = analysis
        result.raw_data["model"] = config.model

        status = analysis.get("tracking_status", "")

        if status == "tracked":
            result.status = CheckStatus.PASS
            result.add_match(f"Task tracked: {analysis.get('explanation')}")
        elif status == "partially_tracked":
            result.status = CheckStatus.WARNING
            result.add_warning(f"Partially tracked: {analysis.get('explanation')}")
        else:
            result.status = CheckStatus.MISSING
            result.add_missing(f"Not in roadmap: {analysis.get('explanation')}")

        for item in analysis.get("matching_items", []):
            result.add_match(f"Matches: {item}")

        if analysis.get("priority_assessment"):
            result.add_match(f"Priority: {analysis.get('priority_assessment')}")

        for dep in analysis.get("dependencies", []):
            result.add_warning(f"Dependency: {dep}")

        for gap in analysis.get("gaps", []):
            result.add_missing(f"Gap: {gap}")

    except Exception as e:
        result.add_warning(f"AI analysis failed: {str(e)}")
        result.status = CheckStatus.MISSING

    return result


def ai_compare_requirements(
    task: str,
    context: RequirementsContext,
    config: Optional[AIConfig] = None
) -> CheckResult:
    """
    Use AI to semantically compare task against requirements.
    """
    config = config or AIConfig()
    result = CheckResult(source="Requirements (AI)")

    req_items = []

    for criteria in context.acceptance_criteria[:5]:
        req_items.append(f"- Acceptance: {criteria[:200]}")

    for criteria in context.success_criteria[:5]:
        req_items.append(f"- Success: {criteria[:200]}")

    for filename in list(context.requirement_files.keys())[:5]:
        req_items.append(f"- File: {filename}")

    if context.estimated_hours:
        req_items.append(f"- Estimated hours: {context.estimated_hours}")

    if context.estimated_loc:
        req_items.append(f"- Estimated LOC: {context.estimated_loc}")

    if not req_items:
        result.add_missing("No requirements data available")
        return result

    requirements_context = "\n".join(req_items)

    prompt = f"""Analyze whether this task has proper requirements and acceptance criteria defined.

TASK: {task}

REQUIREMENTS DATA:
{requirements_context}

Respond in JSON format:
{{
    "requirements_status": "complete" | "partial" | "missing",
    "confidence": 0.0-1.0,
    "acceptance_criteria_quality": "clear" | "vague" | "missing",
    "success_criteria_quality": "clear" | "vague" | "missing",
    "missing_requirements": ["what's missing"],
    "scope_concerns": ["any scope creep or ambiguity issues"],
    "testability": "easy" | "moderate" | "difficult" | "unknown",
    "explanation": "brief explanation"
}}"""

    try:
        client = get_openai_client(config)
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": "You are a business analyst evaluating task requirements completeness."},
                {"role": "user", "content": prompt}
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            response_format={"type": "json_object"}
        )

        analysis = json.loads(response.choices[0].message.content)

        result.raw_data["ai_analysis"] = analysis
        result.raw_data["model"] = config.model

        status = analysis.get("requirements_status", "")

        if status == "complete":
            result.status = CheckStatus.PASS
            result.add_match(f"Requirements complete: {analysis.get('explanation')}")
        elif status == "partial":
            result.status = CheckStatus.WARNING
            result.add_warning(f"Partial requirements: {analysis.get('explanation')}")
        else:
            result.status = CheckStatus.MISSING
            result.add_missing(f"Requirements missing: {analysis.get('explanation')}")

        if analysis.get("acceptance_criteria_quality"):
            result.add_match(f"Acceptance criteria: {analysis.get('acceptance_criteria_quality')}")

        if analysis.get("testability"):
            result.add_match(f"Testability: {analysis.get('testability')}")

        for missing in analysis.get("missing_requirements", []):
            result.add_missing(f"Missing: {missing}")

        for concern in analysis.get("scope_concerns", []):
            result.add_warning(f"Scope concern: {concern}")

    except Exception as e:
        result.add_warning(f"AI analysis failed: {str(e)}")
        result.status = CheckStatus.MISSING

    return result


def ai_cross_source_coherence(
    task: str,
    blueprint: BlueprintContext,
    codebase: CodebaseContext,
    roadmap: RoadmapContext,
    requirements: RequirementsContext,
    config: Optional[AIConfig] = None
) -> CheckResult:
    """
    Use AI to check coherence across all sources of truth.
    """
    config = config or AIConfig()
    result = CheckResult(source="Cross-Source Coherence (AI)")

    summary = f"""
TASK: {task}

BLUEPRINT: {len(blueprint.diagrams)} diagrams, {len(blueprint.components)} components
CODEBASE: {len(codebase.files)} files, {len(codebase.existing_implementations)} similar implementations
ROADMAP: {len(roadmap.matches)} matches, {len(roadmap.monday_items)} Monday items
REQUIREMENTS: {len(requirements.acceptance_criteria)} acceptance criteria, {len(requirements.requirement_files)} files
"""

    prompt = f"""Analyze cross-source coherence for this task across all sources of truth.

{summary}

Consider:
1. Do all sources agree on scope?
2. Are there naming inconsistencies?
3. Is the task properly tracked everywhere?
4. Are there gaps between sources?

Respond in JSON format:
{{
    "coherence_level": "high" | "medium" | "low",
    "confidence": 0.0-1.0,
    "agreements": ["areas where sources agree"],
    "inconsistencies": ["conflicts or naming issues"],
    "gaps": ["missing from certain sources"],
    "recommendations": ["actions to improve coherence"],
    "explanation": "overall coherence assessment"
}}"""

    try:
        client = get_openai_client(config)
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": "You are a systems analyst checking cross-source coherence and traceability."},
                {"role": "user", "content": prompt}
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            response_format={"type": "json_object"}
        )

        analysis = json.loads(response.choices[0].message.content)

        result.raw_data["ai_analysis"] = analysis
        result.raw_data["model"] = config.model

        level = analysis.get("coherence_level", "")

        if level == "high":
            result.status = CheckStatus.PASS
            result.add_match(f"High coherence: {analysis.get('explanation')}")
        elif level == "medium":
            result.status = CheckStatus.WARNING
            result.add_warning(f"Medium coherence: {analysis.get('explanation')}")
        else:
            result.status = CheckStatus.FAIL
            result.add_conflict(f"Low coherence: {analysis.get('explanation')}")

        for agreement in analysis.get("agreements", []):
            result.add_match(f"Agreement: {agreement}")

        for inconsistency in analysis.get("inconsistencies", []):
            result.add_conflict(f"Inconsistency: {inconsistency}")

        for gap in analysis.get("gaps", []):
            result.add_missing(f"Gap: {gap}")

        for rec in analysis.get("recommendations", []):
            result.add_warning(f"Recommendation: {rec}")

    except Exception as e:
        result.add_warning(f"AI analysis failed: {str(e)}")
        result.status = CheckStatus.MISSING

    return result
