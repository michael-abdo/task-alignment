# Task Alignment System

A coherence-checking system that validates incoming tasks against multiple sources of truth for the **XcellerateEQ** real-time meeting analytics platform.

## Overview

This repository contains tools for:
- **Task Alignment** - Validate tasks against Blueprint, Codebase, Roadmap, and Requirements
- **Email Operations** - Download and send emails via Microsoft Graph API
- **Monday.com Integration** - Project management via GraphQL API
- **MCP Server** - Model Context Protocol server for AI-assisted operations

## Project Structure

```
task-alignment/
├── task-alignment/          # Core alignment system
│   ├── checker.py           # Main entry point
│   ├── fetchers.py          # Context fetchers for each source
│   ├── comparators.py       # Comparison logic with alias mapping
│   ├── models.py            # Data models (Report, CheckResult, etc.)
│   ├── ai_comparator.py     # OpenAI-powered semantic comparison
│   └── cli.py               # Command-line interface
├── all_context/
│   ├── Blueprint Diagrams/  # Mermaid architecture diagrams (.mmd/.svg)
│   └── roadmap/             # Roadmap prompts and definitions
├── downloads/
│   ├── attachments/         # Downloaded email attachments
│   ├── email_contents/      # Parsed email content
│   └── sharepoint/          # SharePoint files (Roadmap xlsx)
├── mcp_server.py            # MCP server for Outlook/Monday.com
├── download_emails.py       # Microsoft Graph email client
├── monday_client.py         # Monday.com GraphQL client
├── task-alignment-system.md # System specification
└── XcellerateEQ_Product_Summary.md
```

## Task Alignment System

Validates tasks against 4 sources of truth:

| Source | Owner | What It Checks |
|--------|-------|----------------|
| **Blueprint** | Mike | Architecture diagrams, component relationships, data flows |
| **Codebase** | Youssef/Patrick | Existing implementations, dependencies, code patterns |
| **Roadmap** | Shanti | Feature registry, sprint assignments, component IDs |
| **Requirements** | Greg | Success criteria, acceptance tests, business logic |

### Usage

```bash
# Check a task against all sources
python -m task-alignment "PLAT-F10 Live Alerts with Severity"

# Verbose output
python -m task-alignment -v "Implement Nudge Cooldown Management"

# Check specific sources only
python -m task-alignment --checks blueprint,codebase "Add new API endpoint"

# AI-powered semantic comparison (requires OPENAI_API_KEY)
python -m task-alignment --ai "voice analysis for detecting frustration"

# Output as JSON
python -m task-alignment --json "Fix tone shift detector"
```

### Alignment Principle

**Components must NOT CONTRADICT the blueprint architecture.**

| Status | Meaning | Action |
|--------|---------|--------|
| **Aligned** | Component documented in blueprint | None needed |
| **Gap** | Not documented, but no conflict | Document when ready |
| **Contradiction** | Violates architecture | **BLOCK** |

## MCP Server

Provides CRUD operations via Model Context Protocol:

```bash
# Run the MCP server
python mcp_server.py
```

### Available Tools

**Email Operations:**
- `list_emails_today` - List today's emails
- `search_emails` - Search by query
- `get_email` - Get email by ID
- `send_email` - Send email
- `download_attachment` - Download attachment

**Monday.com Operations:**
- `list_monday_boards` - List boards
- `list_monday_items` - List items in board
- `create_monday_item` - Create new item
- `update_monday_item` - Update item

**SharePoint Operations:**
- `search_sharepoint_files` - Search files
- `download_sharepoint_file` - Download file

## Configuration

Required environment variables (loaded from `.env`):

```bash
# Microsoft Graph API
MS_CLIENT_ID=your_client_id
MS_CLIENT_SECRET=your_client_secret
MS_TENANT_ID=your_tenant_id
MS_USER_EMAIL=your_email

# Monday.com
MONDAY_API_KEY=your_api_key

# OpenAI (optional, for AI mode)
OPENAI_API_KEY=your_openai_key
```

## XcellerateEQ Context

This system supports development of **XcellerateEQ**, a real-time meeting analytics platform that detects:

- **Interruption** - Speaker cut-offs indicating power dynamics
- **Dominance** - Disproportionate talk time
- **Tone Shift** - Emotional changes via Hume AI
- **Anchoring** - First suggestions unduly influencing outcomes
- **Groupthink** - Rapid, uncritical agreement patterns

## Blueprint Diagrams

The `all_context/Blueprint Diagrams/` folder contains Mermaid architecture diagrams:

| Diagram | Description |
|---------|-------------|
| `chunk1_01_current_implementation.mmd` | Current system architecture |
| `chunk2_07_flashpoint_fusion_v1.mmd` | Flashpoint detection & alerts |
| `chunk4_01_psychometric_profile_overlay.mmd` | Psychometric profiles & post-meeting reports |
| `chunk3_01_unified_event_architecture.mmd` | Event processing pipeline |

## Current Alignment Status

As of 2026-01-22:
- **Total Components:** 18
- **Aligned:** 18/18 (100%)
- **Contradictions:** 0

See `all_context/Blueprint Diagrams/ALIGNMENT_PRINCIPLES.md` for details.

## License

Proprietary - XcellerateEQ / Xenodex
