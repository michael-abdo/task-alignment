# Task Alignment System

## Overview

A coherence-checking system that validates incoming tasks against multiple sources of truth, ensuring alignment across architecture, codebase, roadmap, and business requirements.

## System Flow

```
┌─────────────────┐
│   INCOMING TASK │
│  (from Monday,  │
│  email, manual) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                  ALIGNMENT CHECKER                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  BLUEPRINT  │  │  CODEBASE   │  │   ROADMAP   │     │
│  │    CHECK    │  │    CHECK    │  │    CHECK    │     │
│  │   (Mike)    │  │(Youssef/    │  │  (Shanti)   │     │
│  │             │  │ Patrick)    │  │             │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │             │
│  ┌──────┴──────┐                   ┌──────┴──────┐     │
│  │ REQUIREMENTS│                   │             │     │
│  │    CHECK    │                   │             │     │
│  │   (Greg)    │                   │             │     │
│  └──────┬──────┘                   │             │     │
│         │                          │             │     │
│         └────────────┬─────────────┘             │     │
│                      │                           │     │
│                      ▼                           │     │
│            ┌─────────────────┐                   │     │
│            │ ALIGNMENT REPORT│                   │     │
│            └─────────────────┘                   │     │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           OUTPUT                         │
├─────────────────────────────────────────┤
│  ✓ Aligned      - proceed with task     │
│  ⚠ Conflicts    - resolve before start  │
│  ? Missing Info - gather more context   │
└─────────────────────────────────────────┘
```

## Pseudo Code

```python
def check_task_alignment(task_description: str) -> AlignmentReport:
    """
    Main entry point: validates a task against all sources of truth.
    Returns a report with alignment status and any conflicts found.
    """
    
    report = AlignmentReport(task=task_description)
    
    # ─────────────────────────────────────────────────────────
    # 1. BLUEPRINT CHECK (Mike's Architecture)
    # ─────────────────────────────────────────────────────────
    blueprint_context = fetch_blueprint_context(task_description)
    # - Load relevant Mermaid diagrams from SharePoint/local
    # - Parse system architecture, component relationships
    # - Identify which architectural components task touches
    
    blueprint_alignment = compare_task_to_blueprint(
        task=task_description,
        architecture=blueprint_context
    )
    # Check: Does task fit within existing architecture?
    # Check: Are proposed components/flows valid?
    # Check: Any architectural constraints violated?
    
    report.add_check("Blueprint", blueprint_alignment)
    
    # ─────────────────────────────────────────────────────────
    # 2. CODEBASE CHECK (Youssef/Patrick's Implementation)
    # ─────────────────────────────────────────────────────────
    codebase_context = fetch_codebase_context(task_description)
    # - Search GitHub for related files/functions
    # - Check existing implementations
    # - Identify dependencies and interfaces
    
    codebase_alignment = compare_task_to_codebase(
        task=task_description,
        code=codebase_context
    )
    # Check: Does similar functionality already exist?
    # Check: Are dependencies available?
    # Check: Does task align with current code patterns?
    
    report.add_check("Codebase", codebase_alignment)
    
    # ─────────────────────────────────────────────────────────
    # 3. ROADMAP CHECK (Shanti's Project Management)
    # ─────────────────────────────────────────────────────────
    roadmap_context = fetch_roadmap_context(task_description)
    # - Query Monday.com for related items
    # - Load Roadmap.xlsx feature registry & components
    # - Check sprint planning and priorities
    
    roadmap_alignment = compare_task_to_roadmap(
        task=task_description,
        roadmap=roadmap_context
    )
    # Check: Is task in the roadmap?
    # Check: Is it prioritized for current sprint?
    # Check: Are dependencies tracked?
    # Check: Does Component ID exist?
    
    report.add_check("Roadmap", roadmap_alignment)
    
    # ─────────────────────────────────────────────────────────
    # 4. REQUIREMENTS CHECK (Greg's Business Logic)
    # ─────────────────────────────────────────────────────────
    requirements_context = fetch_requirements_context(task_description)
    # - Search email attachments (CSVs) for related requirements
    # - Load acceptance criteria from Greg's files
    # - Check success criteria definitions
    
    requirements_alignment = compare_task_to_requirements(
        task=task_description,
        requirements=requirements_context
    )
    # Check: Are acceptance criteria defined?
    # Check: Does task match business requirements?
    # Check: Any scope conflicts with Greg's specs?
    
    report.add_check("Requirements", requirements_alignment)
    
    # ─────────────────────────────────────────────────────────
    # 5. CROSS-SOURCE COHERENCE CHECK
    # ─────────────────────────────────────────────────────────
    cross_check = check_cross_source_coherence(
        blueprint=blueprint_context,
        codebase=codebase_context,
        roadmap=roadmap_context,
        requirements=requirements_context
    )
    # Check: Do all sources agree on scope?
    # Check: Any conflicting definitions?
    # Check: Is naming consistent across sources?
    
    report.add_check("Cross-Source Coherence", cross_check)
    
    # ─────────────────────────────────────────────────────────
    # 6. GENERATE FINAL REPORT
    # ─────────────────────────────────────────────────────────
    report.compute_overall_status()
    # Status: ALIGNED | CONFLICTS | MISSING_INFO
    
    return report


# ═══════════════════════════════════════════════════════════
# CONTEXT FETCHERS (MCP Integration Points)
# ═══════════════════════════════════════════════════════════

def fetch_blueprint_context(task: str) -> BlueprintContext:
    """
    Fetch relevant architecture diagrams and design docs.
    
    Sources:
    - SharePoint: /sites/DevTeam/blueprints/
    - Local: mermaid files, architecture docs
    
    MCP Tools:
    - search_sharepoint_files(query=task_keywords)
    - download_sharepoint_file(...)
    - Read local .mmd/.md files
    """
    # Extract key terms from task
    keywords = extract_keywords(task)
    
    # Search for relevant diagrams
    diagrams = sharepoint.search_files(
        site_id=DEV_TEAM_SITE,
        query=f"{keywords} mermaid OR architecture OR blueprint"
    )
    
    # Load and parse diagram content
    context = BlueprintContext()
    for diagram in diagrams:
        content = download_and_parse(diagram)
        context.add_diagram(content)
    
    return context


def fetch_codebase_context(task: str) -> CodebaseContext:
    """
    Fetch relevant code from GitHub repositories.
    
    Sources:
    - GitHub: XcellerateEQ repositories
    - Local clone (if available)
    
    MCP Tools:
    - GitHub API (search code, get file contents)
    - Local Grep/Glob tools
    """
    keywords = extract_keywords(task)
    
    context = CodebaseContext()
    
    # Search for relevant files
    relevant_files = github.search_code(
        org="XcellerateEQ",
        query=keywords
    )
    
    # Get file contents and structure
    for file in relevant_files:
        content = github.get_file_content(file.path)
        context.add_file(file.path, content)
    
    # Check for existing implementations
    context.existing_implementations = find_similar_code(task)
    
    return context


def fetch_roadmap_context(task: str) -> RoadmapContext:
    """
    Fetch roadmap data from Monday.com and Roadmap spreadsheet.
    
    Sources:
    - Monday.com boards
    - Roadmap-SourceDoc-v08.xlsx (SharePoint)
    
    MCP Tools:
    - list_monday_boards()
    - list_monday_items(board_id)
    - search_sharepoint_files(query="Roadmap")
    """
    context = RoadmapContext()
    
    # Get Monday.com items
    boards = monday.list_boards()
    for board in boards:
        items = monday.list_items(board.id)
        context.add_monday_items(items)
    
    # Load Roadmap spreadsheet
    roadmap_file = sharepoint.download_file(
        site_id=DEV_TEAM_SITE,
        filename="Roadmap-SourceDoc-*.xlsx"
    )
    
    # Parse feature registry and components
    context.features = parse_feature_registry(roadmap_file)
    context.components = parse_components(roadmap_file)
    
    # Find matching items
    context.matches = find_roadmap_matches(task, context)
    
    return context


def fetch_requirements_context(task: str) -> RequirementsContext:
    """
    Fetch requirements from Greg's email attachments.
    
    Sources:
    - Outlook email attachments (CSVs, Excel files)
    - Downloaded attachment files
    
    MCP Tools:
    - search_emails(query=task_keywords, folder="Archive")
    - list_email_attachments(email_id)
    - download_attachment(...)
    """
    context = RequirementsContext()
    
    # Search Greg's emails for relevant requirements
    emails = outlook.search_emails(
        query=f"from:Greg {extract_keywords(task)}",
        folder="All"
    )
    
    # Get attachments from relevant emails
    for email in emails:
        if email.has_attachments:
            attachments = outlook.list_attachments(email.id)
            for att in attachments:
                if att.name.endswith(('.csv', '.xlsx')):
                    content = outlook.download_attachment(
                        email.id, att.id
                    )
                    context.add_requirement_file(att.name, content)
    
    # Parse acceptance criteria
    context.acceptance_criteria = extract_acceptance_criteria(
        context.requirement_files
    )
    
    return context


# ═══════════════════════════════════════════════════════════
# COMPARISON FUNCTIONS
# ═══════════════════════════════════════════════════════════

def compare_task_to_blueprint(task: str, architecture: BlueprintContext) -> CheckResult:
    """
    Compare task against architectural constraints.
    
    Returns:
    - ALIGNED: Task fits within architecture
    - CONFLICT: Task violates architectural patterns
    - MISSING: No relevant architecture found
    """
    result = CheckResult(source="Blueprint")
    
    # Check if task components exist in architecture
    task_components = extract_components(task)
    for component in task_components:
        if component in architecture.components:
            result.add_match(component, architecture.get_diagram(component))
        else:
            result.add_missing(f"Component '{component}' not in architecture")
    
    # Check data flows
    task_flows = extract_data_flows(task)
    for flow in task_flows:
        if not architecture.validates_flow(flow):
            result.add_conflict(f"Data flow '{flow}' not supported")
    
    return result


def compare_task_to_codebase(task: str, code: CodebaseContext) -> CheckResult:
    """
    Compare task against existing codebase.
    """
    result = CheckResult(source="Codebase")
    
    # Check for existing implementations
    if code.existing_implementations:
        result.add_warning(
            f"Similar code exists: {code.existing_implementations}"
        )
    
    # Check dependencies
    required_deps = extract_dependencies(task)
    for dep in required_deps:
        if dep not in code.available_dependencies:
            result.add_missing(f"Dependency '{dep}' not available")
    
    return result


def compare_task_to_roadmap(task: str, roadmap: RoadmapContext) -> CheckResult:
    """
    Compare task against roadmap and Monday.com.
    """
    result = CheckResult(source="Roadmap")
    
    # Check if task is in roadmap
    if roadmap.matches:
        for match in roadmap.matches:
            result.add_match(
                f"Found in roadmap: {match.feature_id} - {match.component_name}"
            )
    else:
        result.add_missing("Task not found in roadmap - needs to be added")
    
    # Check sprint assignment
    if not roadmap.is_in_current_sprint(task):
        result.add_warning("Task not in current sprint")
    
    return result


def compare_task_to_requirements(task: str, requirements: RequirementsContext) -> CheckResult:
    """
    Compare task against Greg's requirements.
    """
    result = CheckResult(source="Requirements")
    
    # Check acceptance criteria
    if requirements.acceptance_criteria:
        result.add_match(
            f"Acceptance criteria found: {requirements.acceptance_criteria}"
        )
    else:
        result.add_missing("No acceptance criteria defined")
    
    # Check success criteria
    if requirements.success_criteria:
        result.add_match(
            f"Success criteria: {requirements.success_criteria}"
        )
    
    return result


# ═══════════════════════════════════════════════════════════
# OUTPUT STRUCTURES
# ═══════════════════════════════════════════════════════════

class AlignmentReport:
    """
    Final report structure returned by check_task_alignment()
    """
    task: str
    checks: List[CheckResult]
    overall_status: Status  # ALIGNED | CONFLICTS | MISSING_INFO
    
    def to_markdown(self) -> str:
        """Generate human-readable report"""
        md = f"# Alignment Report: {self.task}\n\n"
        md += f"**Overall Status:** {self.overall_status.emoji} {self.overall_status.name}\n\n"
        
        for check in self.checks:
            md += f"## {check.source}\n"
            md += f"Status: {check.status.emoji}\n"
            for item in check.items:
                md += f"- {item}\n"
            md += "\n"
        
        return md


class CheckResult:
    """
    Result of checking task against one source of truth
    """
    source: str  # "Blueprint", "Codebase", "Roadmap", "Requirements"
    status: Status
    matches: List[str]      # Things that align
    conflicts: List[str]    # Things that conflict
    missing: List[str]      # Things not found
    warnings: List[str]     # Non-blocking concerns
```

## Example Usage

### Input
```
Task: "Implement Dissent Language Pattern Matcher component for detecting 
disagreement phrases in meeting transcripts"
```

### Output
```markdown
# Alignment Report: Dissent Language Pattern Matcher

**Overall Status:** ✓ ALIGNED

## Blueprint
Status: ✓
- Component exists in CORE signal processing architecture
- Data flow: Transcript → NLP Pipeline → Signal Output ✓

## Codebase  
Status: ⚠
- Similar pattern matching exists in `claude_client.py` (fake_tone_for_turn)
- Recommend: Refactor existing code rather than new implementation

## Roadmap
Status: ✓
- Found: CORE-F16 | C01 - Dissent Language Pattern Matcher
- Sprint: Current (MVP Priority)
- Owner: Unassigned

## Requirements
Status: ✓
- Acceptance Criteria: "Pass if disagreement phrases detected with >75% recall"
- Success Criteria: Defined in Priority_Signals_Mike_Acceptance_Done_v3.xlsx
- Est. Hours: 2hrs / ~50 LOC

## Cross-Source Coherence
Status: ✓
- All sources reference same component definition
- Naming consistent across roadmap and requirements
```

## Implementation Notes

1. **Start Simple**: Begin with Roadmap + Requirements checks (highest value)
2. **Add Incrementally**: Layer in Blueprint and Codebase checks over time
3. **Cache Strategically**: Cache roadmap/requirements data locally, fetch code on-demand
4. **Human in Loop**: Always surface conflicts for human decision, don't auto-resolve

## Next Steps

- [ ] Create MCP skill that runs this alignment check
- [ ] Integrate with Monday.com task creation workflow
- [ ] Build caching layer for frequently-accessed sources
- [ ] Add Slack/email notifications for conflicts
