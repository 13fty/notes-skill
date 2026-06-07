#!/usr/bin/env python3
"""Parse an agent session transcript into structured knowledge.

Three primary modules (per obsidian-skill-design.md):

  Module A — Tech Stack Extraction
    extract_tech_stack(text) → dict[str, list[str]]
    Uses TECH_REGISTRY + _TECH_LOOKUP for fast matching.

  Module B — Q&A Pair Extraction
    extract_qa_pairs(text) → list[QAPair]
    Paragraph-based: split by blank lines, match problem/solution signals,
    forward-look ≤3 paragraphs for resolution.

  Module C — Wiki Linking
    linkify(text, known_projects, vault_root=None) → str
    Date → [[Daily/...]], tech → [[Tech/...]], first-occurrence-only,
    longest-match-first for project names.

Secondary modules:
  - Note type detection (snippet, concept, tech_card, ADR)
  - Change detection
  - Project name inference
  - Summary generation

Usage:
    python scripts/parse_session.py --session-text "..." --output parsed.json
    python scripts/parse_session.py --session-text "..." --project "MyApp" --date 2026-06-07
    cat session.txt | python scripts/parse_session.py
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════════
# Module A — Tech Stack Extraction
# ═══════════════════════════════════════════════════════════════════════════════

TECH_REGISTRY: dict[str, list[str]] = {
    "Language": [
        "Python", "TypeScript", "JavaScript", "Swift", "Rust", "Go", "Kotlin",
        "Java", "C++", "C#", "Ruby", "PHP", "Bash", "Shell",
    ],
    "Framework": [
        "FastAPI", "Flask", "Django", "React", "Vue", "Next.js", "Nuxt",
        "PyQt5", "PyQt6", "SwiftUI", "UIKit", "Express", "NestJS", "Spring",
        "Rails", "Laravel",
    ],
    "Tool": [
        "Docker", "Git", "npm", "pip", "Homebrew", "Make", "Webpack", "Vite",
        "Pytest", "Jest", "GitHub Actions", "Nginx", "Caddy",
    ],
    "API": [
        "Anthropic", "OpenAI", "DeepSeek", "Gemini", "Claude", "WeChat",
        "Telegram", "Slack", "AWS", "GCP", "Azure", "Vercel", "Railway",
    ],
    "Library": [
        "OpenCV", "MediaPipe", "NumPy", "Pandas", "Matplotlib", "SQLAlchemy",
        "Pydantic", "Uvicorn", "aiohttp", "requests", "Tailwind", "shadcn",
    ],
    "Concept": [
        "REST", "GraphQL", "WebSocket", "gRPC", "IPC", "PTY", "MVC", "MVVM",
        "microservices", "RAG", "embeddings", "LLM", "AI agent",
    ],
}

# Flat lookup: lowercase_name → (category, canonical_name)
_TECH_LOOKUP: dict[str, tuple[str, str]] = {}
for _cat, _techs in TECH_REGISTRY.items():
    for _t in _techs:
        _TECH_LOOKUP[_t.lower()] = (_cat, _t)


def _tokenize(text: str) -> list[str]:
    """Tokenize text into words, preserving dotted/hashed names like Next.js, C#."""
    return re.findall(r"[\w.#/+\-]+", text)


def extract_tech_stack(text: str) -> dict[str, list[str]]:
    """Scan text for known technology names and classify by category.

    Returns {category: [canonical_tech_names]} for matched technologies.
    """
    tokens = {t.lower() for t in _tokenize(text)}
    found: dict[str, set[str]] = {}

    # Direct token match against lookup
    for token_lower in tokens:
        if token_lower in _TECH_LOOKUP:
            cat, canonical = _TECH_LOOKUP[token_lower]
            found.setdefault(cat, set()).add(canonical)

    # Also try substring matching for compound names (e.g. "GitHub Actions" in text)
    text_lower = text.lower()
    for tech_lower, (cat, canonical) in _TECH_LOOKUP.items():
        if " " in tech_lower and tech_lower in text_lower:
            found.setdefault(cat, set()).add(canonical)

    return {cat: sorted(techs) for cat, techs in found.items()}


def tech_to_markdown_table(tech_stack: dict[str, list[str]]) -> str:
    """Convert a tech_stack dict into a Markdown table string."""
    if not tech_stack:
        return "| Category | Technologies |\n|----------|-------------|\n"
    lines = ["| Category | Technologies |", "|----------|-------------|"]
    for cat in ["Language", "Framework", "Tool", "API", "Library", "Concept"]:
        techs = " · ".join(tech_stack.get(cat, []))
        if techs:
            lines.append(f"| {cat} | {techs} |")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Module B — Q&A Pair Extraction
# ═══════════════════════════════════════════════════════════════════════════════

PROBLEM_SIGNALS = [
    r"error[:\s]", r"报错", r"错误", r"问题", r"怎么", r"为什么", r"如何",
    r"坏了", r"不行", r"出问题了", r"失败",
    r"Error", r"Exception", r"issue", r"bug", r"not working",
    r"doesn.t work", r"failed", r"why is", r"why does", r"how do",
    r"how can", r"broken", r"crash",
]

SOLUTION_SIGNALS = [
    r"fix(ed)?", r"解决了", r"工作了", r"成功了", r"修复", r"搞定",
    r"好了", r"可以了", r"办法是",
    r"solution", r"resolved", r"solved", r"try[:\s]", r"instead",
    r"should", r"workaround", r"the fix is",
]


@dataclass
class QAPair:
    """A problem-solution pair extracted from session text."""
    title: str
    problem: str
    solution: str
    tags: list[str] = field(default_factory=list)


def extract_qa_pairs(text: str) -> list[QAPair]:
    """Extract problem-solution pairs using paragraph-based matching.

    Splits text by blank lines into paragraphs, scans each for problem signals,
    then looks forward ≤3 paragraphs for a solution signal.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) < 2:
        return []

    problem_re = re.compile("|".join(PROBLEM_SIGNALS), re.IGNORECASE)
    solution_re = re.compile("|".join(SOLUTION_SIGNALS), re.IGNORECASE)

    pairs: list[QAPair] = []
    seen_problems: set[str] = set()  # Dedup by problem text

    for i, para in enumerate(paragraphs):
        if not problem_re.search(para):
            continue
        if len(para) < 10:
            continue

        # Look forward ≤3 paragraphs for a solution
        solution_text = ""
        for j in range(i + 1, min(i + 4, len(paragraphs))):
            if solution_re.search(paragraphs[j]):
                solution_text = paragraphs[j]
                break

        if solution_text:
            title = para[:80].strip()
            if title not in seen_problems:
                seen_problems.add(title)
                pairs.append(QAPair(
                    title=title,
                    problem=para[:500],
                    solution=solution_text[:500],
                    tags=_infer_tags(para + " " + solution_text),
                ))

    return pairs[:5]  # Cap at 5


def qa_to_markdown(pairs: list[QAPair], date_str: str = "", project: str = "") -> str:
    """Convert QAPair list to Markdown entries."""
    parts: list[str] = []
    for p in pairs:
        tags_str = " ".join(p.tags) if p.tags else "#general"
        entry = f"### {p.title}\n"
        if date_str:
            entry += f"**Date**: {date_str}\n"
        if project:
            entry += f"**Project**: [[{project}]]\n"
        entry += f"\n**Problem**:\n{p.problem}\n\n"
        entry += f"**Solution**:\n{p.solution}\n\n"
        entry += f"**Tags**: {tags_str}\n\n---\n"
        parts.append(entry)
    return "\n".join(parts)


def _infer_tags(text: str) -> list[str]:
    """Infer simple tags from text content."""
    tag_map = {
        "docker": "#docker", "error": "#debug", "报错": "#debug",
        "bug": "#debug", "deploy": "#deployment", "部署": "#deployment",
        "api": "#api", "database": "#database", "数据库": "#database",
        "ui": "#ui", "test": "#testing", "测试": "#testing",
        "auth": "#auth", "login": "#auth", "登录": "#auth",
        "performance": "#performance", "性能": "#performance", "optimize": "#performance",
    }
    lower = text.lower()
    tags = sorted({tag for keyword, tag in tag_map.items() if keyword in lower})
    # Add category-based tags
    for cat, techs in TECH_REGISTRY.items():
        for tech in techs:
            if tech.lower() in lower:
                tags.append(f"#{cat.lower()}")
    return sorted(set(tags))


# ═══════════════════════════════════════════════════════════════════════════════
# Module C — Wiki Linking
# ═══════════════════════════════════════════════════════════════════════════════

_DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def linkify(
    text: str,
    known_projects: list[str] | None = None,
    vault_root: str | None = None,
) -> str:
    """Replace plain-text references with Obsidian [[WikiLinks]].

    Rules:
    - Dates (YYYY-MM-DD) → [[Daily/YYYY-MM-DD]]
    - Known project names → [[Projects/ProjectName]]
    - Tech names from TECH_REGISTRY → [[Knowledge/TechName]]
    - First occurrence only per entity (subsequent occurrences stay as plain text)

    Project names are matched longest-first to avoid substring collisions.
    """
    known_projects = known_projects or []
    linked: set[str] = set()

    result = text

    # 1. Link dates (first occurrence only)
    def _link_date(m: re.Match) -> str:
        date_str = m.group(1)
        if date_str not in linked:
            linked.add(date_str)
            return f"[[Daily/{date_str}]]"
        return date_str
    result = _DATE_PATTERN.sub(_link_date, result)

    # 2. Link project names (longest-match-first)
    for proj in sorted(known_projects, key=len, reverse=True):
        if proj not in linked:
            # Match whole-word project name, not already inside a link
            pattern = rf"(?<!\[\[)(?<!\w){re.escape(proj)}(?!\w)(?!\]\])"
            m = re.search(pattern, result)
            if m:
                linked.add(proj)
                result = re.sub(pattern, f"[[Projects/{proj}]]", result, count=1)

    # 3. Link tech names (first occurrence, not inside existing links)
    for tech_lower, (_cat, canonical) in sorted(
        _TECH_LOOKUP.items(), key=lambda x: -len(x[0])
    ):
        if canonical not in linked and len(canonical) >= 3:
            pattern = rf"(?<!\[\[)(?<!\w){re.escape(canonical)}(?!\w)(?!\]\])"
            m = re.search(pattern, result, re.IGNORECASE)
            if m:
                linked.add(canonical)
                result = re.sub(
                    pattern,
                    f"[[Knowledge/{canonical}]]",
                    result,
                    count=1,
                    flags=re.IGNORECASE,
                )

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Secondary — Change Detection
# ═══════════════════════════════════════════════════════════════════════════════

CHANGE_SIGNALS_ZH = [
    "新增了", "实现了", "修复了", "重构了", "改进了", "添加了",
    "删除了", "优化了", "完成了", "部署了",
]
CHANGE_SIGNALS_EN = [
    "added", "implemented", "fixed", "refactored", "improved",
    "removed", "optimized", "built", "created", "deployed", "updated", "migrated",
]


def detect_changes(text: str) -> list[str]:
    """Detect lines that describe changes made during the session."""
    changes = []
    all_signals = CHANGE_SIGNALS_ZH + CHANGE_SIGNALS_EN
    for line in text.split("\n"):
        stripped = line.strip()
        if any(sig in stripped for sig in all_signals):
            if len(stripped) > 10:
                changes.append(stripped[:200])
    return changes[:10]


# ═══════════════════════════════════════════════════════════════════════════════
# Secondary — Project Name Inference
# ═══════════════════════════════════════════════════════════════════════════════

def infer_project_name(text: str) -> str:
    """Infer the project name from conversation context. Returns '通用' if unclear."""
    patterns = [
        r"project[:\s]+['\"]?(\w[\w\s-]+\w)",
        r"Project[:\s]+['\"]?(\w[\w\s-]+\w)",
        r"项目[:\s]+['\"]?(\w[\w\s-]+\w)",
        r"#\s*(\w[\w\s-]+\w)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            name = m.group(1).strip()
            if len(name) > 2 and name.lower() not in (
                "project", "项目", "overview", "summary", "todo", "notes",
            ):
                return name
    return "通用"


# ═══════════════════════════════════════════════════════════════════════════════
# Secondary — Summary Generation
# ═══════════════════════════════════════════════════════════════════════════════

def summarize_topic(text: str) -> str:
    """Produce a one-line session topic."""
    for line in text.split("\n"):
        stripped = line.strip()
        if len(stripped) > 10 and not stripped.startswith(("#", ">", "```", "User:", "AI:")):
            return stripped[:100]
    return "Session"


def summarize(text: str) -> str:
    """Produce a brief (≤3 sentence) summary."""
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
    if not lines:
        return "No summary available."
    return " ".join(lines[:3])[:300]


def detect_open_issues(text: str) -> list[str]:
    """Detect unresolved items or next-step blockers."""
    issues = []
    sigs = ["未解决", "还没", "待解决", "下一步", "TODO", "FIXME",
            "not yet", "pending", "unresolved", "next step"]
    for line in text.split("\n"):
        stripped = line.strip()
        if any(sig in stripped for sig in sigs):
            issues.append(stripped[:120])
    return issues[:5]


def detect_next_actions(text: str) -> list[str]:
    """Detect planned next actions."""
    actions = []
    sigs = ["下一步", "接下来", "计划", "准备",
            "next step", "plan to", "going to", "will add", "will implement"]
    for line in text.split("\n"):
        stripped = line.strip()
        if any(sig in stripped for sig in sigs):
            actions.append(stripped[:120])
    return actions[:5]


# ═══════════════════════════════════════════════════════════════════════════════
# Secondary — Knowledge Node Detection
# ═══════════════════════════════════════════════════════════════════════════════

def _classify_knowledge_type(category: str) -> str:
    """Map TECH_REGISTRY category to Knowledge Node type."""
    return {
        "Language": "tool",
        "Framework": "framework",
        "Tool": "tool",
        "API": "tool",
        "Library": "framework",
        "Concept": "concept",
    }.get(category, "tool")


def _extract_code_blocks(text: str) -> list[dict]:
    """Extract non-boilerplate code blocks from text."""
    blocks = []
    code_matches = re.findall(r"```(\w+)?\n(.*?)```", text, re.DOTALL)
    for lang, code in code_matches:
        code = code.strip()
        lines = code.split("\n")
        if len(lines) >= 5:
            boilerplate = sum(
                1 for line in lines
                if line.strip().startswith(("import ", "from ", "#", "//", "export ", "require(", "const {"))
            )
            if (boilerplate / len(lines)) <= 0.7:
                blocks.append({"language": lang or "text", "code": code})
    return blocks[:3]


def detect_note_types(text: str, tech_stack: dict[str, list[str]]) -> list[dict]:
    """Detect knowledge nodes to create/update from this session.

    Returns a unified list of knowledge_node entries. Each tech found becomes a
    knowledge node in Knowledge/. Code blocks are attached to their primary tech's node.
    """
    knowledge_nodes: list[dict] = []
    code_blocks = _extract_code_blocks(text)

    all_techs: list[tuple[str, str]] = []
    for cat, techs in tech_stack.items():
        for tech in techs:
            all_techs.append((cat, tech))

    for category, tech in all_techs:
        # Find any code blocks that reference this tech
        related_code = [
            cb for cb in code_blocks
            if tech.lower() in cb["code"].lower()
        ]
        knowledge_nodes.append({
            "type": "knowledge_node",
            "name": tech,
            "node_type": _classify_knowledge_type(category),
            "description": f"{tech} — {category.lower()}",
            "code_blocks": related_code,
            "is_first_seen": not _has_been_seen_before(text, tech),
            "pitfalls": [],
            "related_concepts": [],
        })

    return knowledge_nodes


def _has_been_seen_before(text: str, tech: str) -> bool:
    """Heuristic: does this look like a first encounter with the tech?"""
    intro_patterns = [
        rf"(?:first.time|new.to|开始用|首次使用|第一次用).*{re.escape(tech)}",
        rf"{re.escape(tech)}.*?(?:is|was)\s+(?:a|the|used|new)",
    ]
    return not any(re.search(p, text, re.IGNORECASE) for p in intro_patterns)


# ═══════════════════════════════════════════════════════════════════════════════
# Main extraction function
# ═══════════════════════════════════════════════════════════════════════════════

def parse_session(
    text: str,
    timestamp: str | None = None,
    project_name: str | None = None,
    date_str: str | None = None,
) -> dict:
    """Main entry point: parse session text into structured knowledge JSON.

    Args:
        text: The full session transcript.
        timestamp: ISO 8601 timestamp. Defaults to now.
        project_name: Override project name inference. If None, inferred from text.
        date_str: Override date (YYYY-MM-DD). If None, derived from timestamp.

    Returns:
        Structured dict ready for sync.py or downstream processing.
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Generate session time (HHMM) for file naming
    now = datetime.now(timezone.utc)
    session_time = now.strftime("%H%M")

    tech_stack = extract_tech_stack(text)
    qa_pairs = extract_qa_pairs(text)
    changes = detect_changes(text)

    # Extract QAPair objects to dicts for JSON serialization
    problems_solved = [
        {
            "title": q.title,
            "problem": q.problem,
            "solution": q.solution,
            "tags": q.tags,
        }
        for q in qa_pairs
    ]

    result = {
        "session_topic": summarize_topic(text),
        "project_name": project_name or infer_project_name(text),
        "summary": summarize(text),
        "session_time": session_time,
        "tech_stack": tech_stack,
        "tech_markdown": tech_to_markdown_table(tech_stack),
        "changes": changes,
        "problems_solved": problems_solved,
        "qa_markdown": qa_to_markdown(qa_pairs, date_str, project_name or infer_project_name(text)),
        "open_issues": detect_open_issues(text),
        "next_actions": detect_next_actions(text),
        "note_types": detect_note_types(text, tech_stack),
        "timestamp": timestamp,
        "date": date_str,
    }

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    text: str | None = None
    output_path: str | None = None
    project_name: str | None = None
    date_str: str | None = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--session-text" and i + 1 < len(args):
            text = args[i + 1]
            i += 2
        elif args[i].startswith("--session-text="):
            text = args[i].split("=", 1)[1]
            i += 1
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        elif args[i].startswith("--output="):
            output_path = args[i].split("=", 1)[1]
            i += 1
        elif args[i] == "--project" and i + 1 < len(args):
            project_name = args[i + 1]
            i += 2
        elif args[i].startswith("--project="):
            project_name = args[i].split("=", 1)[1]
            i += 1
        elif args[i] == "--date" and i + 1 < len(args):
            date_str = args[i + 1]
            i += 2
        elif args[i].startswith("--date="):
            date_str = args[i].split("=", 1)[1]
            i += 1
        else:
            i += 1

    # Read from stdin if no --session-text provided
    if text is None:
        text = sys.stdin.read()

    if not text.strip():
        print(json.dumps({"error": "No input text provided"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    result = parse_session(text, project_name=project_name, date_str=date_str)
    json_output = json.dumps(result, ensure_ascii=False, indent=2)

    if output_path:
        Path(output_path).write_text(json_output + "\n", encoding="utf-8")
        print(f"Extracted knowledge written to {output_path}")
    else:
        print(json_output)


if __name__ == "__main__":
    main()
