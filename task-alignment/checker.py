"""Main entry point for Task Alignment System.

Orchestrates fetching context from all sources and comparing against the task.
"""

from __future__ import annotations

from typing import Optional, List
from pathlib import Path

from .models import AlignmentReport
from .fetchers import (
    fetch_blueprint_context,
    fetch_codebase_context,
    fetch_roadmap_context,
    fetch_requirements_context,
)
from .comparators import (
    compare_task_to_blueprint,
    compare_task_to_codebase,
    compare_task_to_roadmap,
    compare_task_to_requirements,
    check_cross_source_coherence,
)


def check_task_alignment(
    task_description: str,
    repo_path: Optional[Path] = None,
    checks: Optional[List[str]] = None,
    verbose: bool = False,
    use_ai: bool = False,
    openai_api_key: Optional[str] = None,
    ai_model: str = "gpt-4o-mini",
) -> AlignmentReport:
    """
    Main entry point: validates a task against all sources of truth.

    Args:
        task_description: The task to validate
        repo_path: Optional path to local code repository
        checks: Optional list of checks to run (blueprint, codebase, roadmap, requirements, coherence)
                If None, runs all checks.
        verbose: If True, print progress
        use_ai: If True, use OpenAI for semantic comparison instead of keyword matching
        openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        ai_model: OpenAI model to use (default: gpt-4o-mini)

    Returns:
        AlignmentReport with alignment status and any conflicts found.
    """
    report = AlignmentReport(task=task_description)

    all_checks = ["blueprint", "codebase", "roadmap", "requirements", "coherence"]
    checks_to_run = checks or all_checks

    # Setup AI config if enabled
    ai_config = None
    if use_ai:
        from .ai_comparator import AIConfig
        ai_config = AIConfig(api_key=openai_api_key, model=ai_model)
        if verbose:
            print(f"Using AI mode with model: {ai_model}")

    contexts = {}

    # ─────────────────────────────────────────────────────────
    # 1. BLUEPRINT CHECK (Mike's Architecture)
    # ─────────────────────────────────────────────────────────
    if "blueprint" in checks_to_run:
        if verbose:
            print("Fetching blueprint context...")

        blueprint_context = fetch_blueprint_context(task_description)
        contexts["blueprint"] = blueprint_context

        if verbose:
            print(f"  Found {len(blueprint_context.diagrams)} relevant diagrams")

        if use_ai:
            from .ai_comparator import ai_compare_blueprint
            blueprint_result = ai_compare_blueprint(task_description, blueprint_context, ai_config)
        else:
            blueprint_result = compare_task_to_blueprint(
                task=task_description,
                architecture=blueprint_context
            )
        report.add_check(blueprint_result)

    # ─────────────────────────────────────────────────────────
    # 2. CODEBASE CHECK (Youssef/Patrick's Implementation)
    # ─────────────────────────────────────────────────────────
    if "codebase" in checks_to_run:
        if verbose:
            print("Fetching codebase context...")

        codebase_context = fetch_codebase_context(task_description, repo_path)
        contexts["codebase"] = codebase_context

        if verbose:
            print(f"  Found {len(codebase_context.files)} relevant files")

        if use_ai:
            from .ai_comparator import ai_compare_codebase
            codebase_result = ai_compare_codebase(task_description, codebase_context, ai_config)
        else:
            codebase_result = compare_task_to_codebase(
                task=task_description,
                code=codebase_context
            )
        report.add_check(codebase_result)

    # ─────────────────────────────────────────────────────────
    # 3. ROADMAP CHECK (Shanti's Project Management)
    # ─────────────────────────────────────────────────────────
    if "roadmap" in checks_to_run:
        if verbose:
            print("Fetching roadmap context...")

        roadmap_context = fetch_roadmap_context(task_description)
        contexts["roadmap"] = roadmap_context

        if verbose:
            print(f"  Found {len(roadmap_context.matches)} roadmap matches")
            print(f"  Found {len(roadmap_context.monday_items)} Monday.com items")

        if use_ai:
            from .ai_comparator import ai_compare_roadmap
            roadmap_result = ai_compare_roadmap(task_description, roadmap_context, ai_config)
        else:
            roadmap_result = compare_task_to_roadmap(
                task=task_description,
                roadmap=roadmap_context
            )
        report.add_check(roadmap_result)

    # ─────────────────────────────────────────────────────────
    # 4. REQUIREMENTS CHECK (Greg's Business Logic)
    # ─────────────────────────────────────────────────────────
    if "requirements" in checks_to_run:
        if verbose:
            print("Fetching requirements context...")

        requirements_context = fetch_requirements_context(task_description)
        contexts["requirements"] = requirements_context

        if verbose:
            print(f"  Found {len(requirements_context.requirement_files)} requirement files")
            print(f"  Found {len(requirements_context.acceptance_criteria)} acceptance criteria")

        if use_ai:
            from .ai_comparator import ai_compare_requirements
            requirements_result = ai_compare_requirements(task_description, requirements_context, ai_config)
        else:
            requirements_result = compare_task_to_requirements(
                task=task_description,
                requirements=requirements_context
            )
        report.add_check(requirements_result)

    # ─────────────────────────────────────────────────────────
    # 5. CROSS-SOURCE COHERENCE CHECK
    # ─────────────────────────────────────────────────────────
    if "coherence" in checks_to_run and len(contexts) >= 2:
        if verbose:
            print("Checking cross-source coherence...")

        if use_ai:
            from .ai_comparator import ai_cross_source_coherence
            coherence_result = ai_cross_source_coherence(
                task=task_description,
                blueprint=contexts.get("blueprint", fetch_blueprint_context("")),
                codebase=contexts.get("codebase", fetch_codebase_context("")),
                roadmap=contexts.get("roadmap", fetch_roadmap_context("")),
                requirements=contexts.get("requirements", fetch_requirements_context("")),
                config=ai_config,
            )
        else:
            coherence_result = check_cross_source_coherence(
                blueprint=contexts.get("blueprint", fetch_blueprint_context("")),
                codebase=contexts.get("codebase", fetch_codebase_context("")),
                roadmap=contexts.get("roadmap", fetch_roadmap_context("")),
                requirements=contexts.get("requirements", fetch_requirements_context("")),
            )
        report.add_check(coherence_result)

    # ─────────────────────────────────────────────────────────
    # 6. COMPUTE FINAL STATUS
    # ─────────────────────────────────────────────────────────
    report.compute_overall_status()

    if verbose:
        print(f"\nOverall status: {report.overall_status.emoji} {report.overall_status.value.upper()}")

    return report


def quick_check(task_description: str) -> str:
    """
    Quick alignment check - returns markdown summary.

    Useful for quick validation without detailed configuration.
    """
    report = check_task_alignment(task_description)
    return report.to_markdown()
