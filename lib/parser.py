"""Conversation text parsers for obsidian-skill.

Extracts structured data from raw AI conversation transcripts:
- Tech stack detection
- Q&A / problem-solution pairs
- Wiki link generation
- Proper noun detection

All functions are pure — text in, structured data out. No I/O.
"""

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# ── Tech Stack Extraction ───────────────────────────────────────────────────────

TECH_REGISTRY: dict[str, list[str]] = {
    "Language": [
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
_tech_lookup: dict[str, tuple[str, str]] = {}
for _cat, _items in TECH_REGISTRY.items():
    for _item in _items:
        _tech_lookup[_item.lower()] = (_cat, _item)


def extract_tech_stack(text: str) -> dict[str, list[str]]:
    """Return {category: [tech, ...]} for all known techs mentioned in text."""
    found: dict[str, set[str]] = {}
    words = re.findall(r"[\w.#/+\-]+", text)
    for word in words:
        key = word.lower().rstrip(".,;:!?")
        if key in _tech_lookup:
            cat, canonical = _tech_lookup[key]
            found.setdefault(cat, set()).add(canonical)

    # Preserve registry category order
    result: dict[str, list[str]] = {}
    for cat in TECH_REGISTRY:
        if cat in found:
            result[cat] = sorted(found[cat])
    return result


def tech_stack_to_markdown(stack: dict[str, list[str]]) -> str:
    """Render a tech stack dict as a Markdown table."""
    if not stack:
        return "_No technologies detected_"
    rows = ["| Category | Technologies |", "|----------|-------------|"]
    for cat, techs in stack.items():
        rows.append(f"| {cat} | {' · '.join(techs)} |")
    return "\n".join(rows)


# ── Q&A Extraction ──────────────────────────────────────────────────────────────

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

_prob_re = re.compile("|".join(PROBLEM_SIGNALS), re.IGNORECASE)
_soln_re = re.compile("|".join(SOLUTION_SIGNALS), re.IGNORECASE)


@dataclass
class QAPair:
    title: str
    problem: str
    solution: str
    tags: list[str] = field(default_factory=list)


def extract_qa_pairs(text: str) -> list[QAPair]:
    """Heuristically extract problem/solution pairs from conversation text."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    pairs: list[QAPair] = []
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        if _prob_re.search(para):
            problem_text = para
            solution_text = ""
            for j in range(i + 1, min(i + 4, len(paragraphs))):
                if _soln_re.search(paragraphs[j]):
                    solution_text = paragraphs[j]
                    i = j
                    break
            if solution_text:
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
    """Render a single QAPair as Markdown."""
    tag_str = " ".join(f"#{t}" for t in qa.tags) if qa.tags else ""
    parts = [
        f"### {qa.title}",
        f"**Date**: {date}",
        f"**Project**: [[{project}]]",
        "",
        "**Problem**:",
        qa.problem,
        "",
        "**Solution**:",
        qa.solution,
    ]
    if tag_str:
        parts.append(f"\n**Tags**: {tag_str}")
    return "\n".join(parts)


# ── Wiki Link Generation ────────────────────────────────────────────────────────

_date_re = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def linkify(text: str, known_projects: list[str], vault_root: Path | None = None) -> str:
    """Replace bare tech names and project references with [[WikiLinks]].

    - Dates → [[Daily/YYYY-MM-DD]]
    - Project names → [[Projects/Name]]
    - First occurrence of each entity only.
    """
    linked: set[str] = set()

    def replace_date(m: re.Match) -> str:
        d = m.group(1)
        if d not in linked:
            linked.add(d)
            return f"[[Daily/{d}]]"
        return d
    text = _date_re.sub(replace_date, text)

    for proj in sorted(known_projects, key=len, reverse=True):
        if proj in linked:
            continue
        pattern = re.compile(r"(?<!\[\[)\b" + re.escape(proj) + r"\b(?!\]\])")
        def replace_proj(m: re.Match, p: str = proj) -> str:
            if p not in linked:
                linked.add(p)
                return f"[[Projects/{p}]]"
            return p
        text = pattern.sub(replace_proj, text)

    return text


# ── Summary helpers ─────────────────────────────────────────────────────────────

def extract_proper_nouns(text: str) -> list[str]:
    """Extract capitalized multi-word phrases that look like proper nouns."""
    pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
    matches = pattern.findall(text)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        if m.lower() not in seen:
            seen.add(m.lower())
            result.append(m)
    return result
