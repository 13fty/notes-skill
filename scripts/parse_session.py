#!/usr/bin/env python3
"""
parse_session.py
================
Helpers for extracting structured data from raw AI conversation text.
Used by the Obsidian skill's Step 4 (tech stack), Step 5 (Q&A), and Step 6 (wiki links).

Can be imported or run standalone:
    python parse_session.py --input session.txt --output parsed.json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path


# ── Tech Stack Extraction ──────────────────────────────────────────────────────

TECH_REGISTRY = {
    "Language":  [
        "Python", "TypeScript", "JavaScript", "Swift", "Rust", "Go", "Kotlin",
        "Java", "C++", "C#", "Ruby", "PHP", "Bash", "Shell",
    ],
    "Framework": [
        "FastAPI", "Flask", "Django", "React", "Vue", "Next.js", "Nuxt",
        "PyQt5", "PyQt6", "SwiftUI", "UIKit", "Express", "NestJS",
        "Spring", "Rails", "Laravel",
    ],
    "Tool": [
        "Docker", "Git", "npm", "pip", "Homebrew", "Make", "Webpack", "Vite",
        "Pytest", "Jest", "GitHub Actions", "CI/CD", "Nginx", "Caddy",
    ],
    "API/Service": [
        "Anthropic", "OpenAI", "DeepSeek", "Gemini", "Claude",
        "WeChat", "Telegram", "Slack", "Discord",
        "AWS", "GCP", "Azure", "Vercel", "Railway",
    ],
    "Library": [
        "OpenCV", "MediaPipe", "NumPy", "Pandas", "Matplotlib",
        "SQLAlchemy", "Pydantic", "Uvicorn", "aiohttp", "requests",
        "python-pptx", "openpyxl", "Pillow",
        "Tailwind", "shadcn", "lucide",
    ],
    "Concept": [
        "REST", "GraphQL", "WebSocket", "gRPC", "IPC", "PTY",
        "MVC", "MVVM", "microservices", "containerization",
        "RAG", "embeddings", "vector database", "LLM", "AI agent",
    ],
}

# Build flat lookup: lowercase tech name → (category, canonical name)
_TECH_LOOKUP: dict[str, tuple[str, str]] = {}
for _cat, _items in TECH_REGISTRY.items():
    for _item in _items:
        _TECH_LOOKUP[_item.lower()] = (_cat, _item)


def extract_tech_stack(text: str) -> dict[str, list[str]]:
    """Return {category: [tech, ...]} for all techs mentioned in text."""
    found: dict[str, set[str]] = {}
    words = re.findall(r"[\w.#/+\-]+", text)
    for word in words:
        key = word.lower().rstrip(".,;:!?")
        if key in _TECH_LOOKUP:
            cat, canonical = _TECH_LOOKUP[key]
            found.setdefault(cat, set()).add(canonical)

    # Preserve registry category order
    result: dict[str, list[str]] = {}
    for cat in TECH_REGISTRY:
        if cat in found:
            result[cat] = sorted(found[cat])
    return result


def tech_stack_to_markdown(stack: dict[str, list[str]]) -> str:
    if not stack:
        return "_No technologies detected_"
    rows = ["| Category | Technologies |", "|----------|-------------|"]
    for cat, techs in stack.items():
        rows.append(f"| {cat} | {' · '.join(techs)} |")
    return "\n".join(rows)


# ── Q&A Extraction ─────────────────────────────────────────────────────────────

PROBLEM_SIGNALS = [
    r"error[:\s]", r"Error[:\s]", r"Exception[:\s]",
    r"报错", r"错误", r"问题", r"issue", r"bug",
    r"why (is|does|doesn't|can't|won't)",
    r"how (do|can|to)",
    r"怎么", r"为什么", r"如何",
    r"not working", r"doesn't work", r"failed",
]

SOLUTION_SIGNALS = [
    r"fix(ed)?[:\s]", r"solution[:\s]", r"resolve[d]?[:\s]",
    r"solved", r"工作了", r"解决了", r"成功了",
    r"try[:\s]", r"instead[:\s]", r"should[:\s]",
    r"the (issue|problem) was",
]

_PROB_RE = re.compile("|".join(PROBLEM_SIGNALS), re.IGNORECASE)
_SOLN_RE = re.compile("|".join(SOLUTION_SIGNALS), re.IGNORECASE)


@dataclass
class QAPair:
    title: str
    problem: str
    solution: str
    tags: list[str] = field(default_factory=list)


def extract_qa_pairs(text: str) -> list[QAPair]:
    """
    Heuristically extract problem/solution pairs from conversation text.
    Returns a list of QAPair objects.
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    pairs: list[QAPair] = []
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        if _PROB_RE.search(para):
            problem_text = para
            solution_text = ""
            # Look ahead up to 3 paragraphs for solution
            for j in range(i + 1, min(i + 4, len(paragraphs))):
                if _SOLN_RE.search(paragraphs[j]):
                    solution_text = paragraphs[j]
                    i = j
                    break
            if solution_text:
                # Generate a short title from first ~8 words of problem
                words = re.findall(r"\w+", problem_text)
                title = " ".join(words[:8])
                pairs.append(QAPair(
                    title=title,
                    problem=problem_text[:400],
                    solution=solution_text[:600],
                ))
        i += 1
    return pairs


def qa_pair_to_markdown(qa: QAPair, project: str, date: str) -> str:
    tag_str = " ".join(f"#{t}" for t in qa.tags) if qa.tags else ""
    return f"""### {qa.title}
**Date**: {date}
**Project**: [[{project}]]

**Problem**:
{qa.problem}

**Solution**:
{qa.solution}
{f'{chr(10)}**Tags**: {tag_str}' if tag_str else ''}"""


# ── Wiki Link Generation ───────────────────────────────────────────────────────

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def linkify(text: str, known_projects: list[str], vault_root: Path | None = None) -> str:
    """
    Replace bare tech names and project names with [[WikiLinks]].
    - Dates → [[Daily/YYYY-MM-DD]]
    - Project names → [[Projects/Name]]
    - First occurrence of each entity only
    """
    linked: set[str] = set()

    # Link dates
    def replace_date(m):
        d = m.group(1)
        if d not in linked:
            linked.add(d)
            return f"[[Daily/{d}]]"
        return d
    text = DATE_RE.sub(replace_date, text)

    # Link project names
    for proj in sorted(known_projects, key=len, reverse=True):
        if proj in linked:
            continue
        pattern = re.compile(r"(?<!\[\[)\b" + re.escape(proj) + r"\b(?!\]\])")
        def replace_proj(m, p=proj):
            if p not in linked:
                linked.add(p)
                return f"[[Projects/{p}]]"
            return p
        text = pattern.sub(replace_proj, text)

    return text


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Parse AI session text for Obsidian skill")
    parser.add_argument("--input", help="Input text file (default: stdin)")
    parser.add_argument("--output", help="Output JSON file (default: stdout)")
    parser.add_argument("--project", default="Unknown", help="Project name for Q&A attribution")
    parser.add_argument("--date", help="Session date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    from datetime import date as _date
    session_date = args.date or str(_date.today())

    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    tech_stack = extract_tech_stack(text)
    qa_pairs = extract_qa_pairs(text)

    result = {
        "date": session_date,
        "project": args.project,
        "tech_stack": tech_stack,
        "tech_markdown": tech_stack_to_markdown(tech_stack),
        "qa_pairs": [asdict(qa) for qa in qa_pairs],
        "qa_markdown": [qa_pair_to_markdown(qa, args.project, session_date) for qa in qa_pairs],
    }

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"[done] Wrote parsed output to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()