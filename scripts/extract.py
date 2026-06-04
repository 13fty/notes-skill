#!/usr/bin/env python3
"""Extract structured knowledge from an agent session conversation.

Reads a conversation transcript (stdin or --session-text) and outputs a JSON object
with summary, project name, tech stack, changes, problems solved, and open issues.

Usage:
    python scripts/extract.py < session.txt
    python scripts/extract.py --session-text "..." --output /tmp/extracted.json
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Classification data ──────────────────────────────────────────────────────

TECH_CATEGORIES = {
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

# Signal words for detecting changes, problems, solutions
CHANGE_SIGNALS_ZH = ["新增了", "实现了", "修复了", "重构了", "改进了", "添加了", "删除了", "优化了"]
CHANGE_SIGNALS_EN = ["added", "implemented", "fixed", "refactored", "improved", "removed", "optimized", "built", "created"]
PROBLEM_SIGNALS_ZH = ["报错", "错误", "问题", "怎么", "为什么", "如何"]
PROBLEM_SIGNALS_EN = ["error", "Error", "Exception", "issue", "bug", "not working", "doesn't work", "failed", "why is", "why does", "how do"]
SOLUTION_SIGNALS_ZH = ["解决了", "工作了", "成功了", "修复"]
SOLUTION_SIGNALS_EN = ["fix", "fixed", "solution", "resolved", "solved", "try", "instead", "should"]

# Note type detection signals
SNIPPET_SIGNALS = [
    "用法", "示例", "save this", "记住这个", "这个有用", "here's how",
    "the trick is", "this is useful", "代码", "code snippet",
]
CONCEPT_SIGNALS_ZH = ["什么是", "是什么", "区别", "原理", "本质上", "核心思想", "我理解了", "原来如此"]
CONCEPT_SIGNALS_EN = ["what is", "explain", "how does", "the idea is", "essentially", "that makes sense"]
ARCH_SIGNALS_ZH = ["放弃", "改用", "选择了", "决定用", "因为", "所以选了", "以后都用", "标准做法"]
ARCH_SIGNALS_EN = ["dropped", "in favor of", "chose", "decided to", "because", "going forward", "standard way", "why X over Y"]
FIRST_USE_SIGNALS = ["第一次用", "首次使用", "开始用", "first time using", "new to", "trying out"]


def detect_tech_stack(text: str) -> dict[str, list[str]]:
    """Scan text for known technology names and classify by category."""
    found: dict[str, list[str]] = {}
    for category, techs in TECH_CATEGORIES.items():
        matched = []
        for tech in techs:
            # Match whole-word where possible, case-sensitive
            if tech.lower() in text.lower():
                matched.append(tech)
        if matched:
            found[category] = sorted(set(matched))
    return found


def detect_changes(text: str) -> list[str]:
    """Detect lines that describe changes made during the session."""
    changes = []
    for line in text.split("\n"):
        line_stripped = line.strip()
        for sig in CHANGE_SIGNALS_ZH + CHANGE_SIGNALS_EN:
            if sig in line_stripped:
                changes.append(line_stripped)
                break
    return changes[:10]  # Cap at 10


def detect_problems(text: str) -> list[dict]:
    """Detect problem-solution pairs in the conversation."""
    problems = []
    lines = text.split("\n")

    problem_signal = PROBLEM_SIGNALS_ZH + PROBLEM_SIGNALS_EN
    solution_signal = SOLUTION_SIGNALS_ZH + SOLUTION_SIGNALS_EN

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if any(sig in line for sig in problem_signal):
            # Found a potential problem — grab context
            problem_text = line
            solution_text = ""
            # Look ahead for a solution within the next 20 lines
            for j in range(i + 1, min(i + 20, len(lines))):
                if any(sig in lines[j].strip() for sig in solution_signal):
                    solution_text = lines[j].strip()
                    break
            if solution_text:
                problems.append({
                    "title": problem_text[:80],
                    "problem": problem_text,
                    "solution": solution_text,
                    "tags": _infer_tags(problem_text + " " + solution_text),
                })
        i += 1

    return problems[:5]  # Cap at 5


def _infer_tags(text: str) -> list[str]:
    """Infer simple tags from text content."""
    tags = []
    tag_map = {
        "docker": "#docker",
        "error": "#debug",
        "报错": "#debug",
        "bug": "#debug",
        "deploy": "#deployment",
        "部署": "#deployment",
        "api": "#api",
        "database": "#database",
        "数据库": "#database",
        "ui": "#ui",
        "test": "#testing",
        "测试": "#testing",
    }
    lower = text.lower()
    for keyword, tag in tag_map.items():
        if keyword in lower:
            tags.append(tag)
    return sorted(set(tags))


def infer_project_name(text: str) -> str:
    """Infer the project name from conversation context. Returns '通用' if unclear."""
    # Look for explicit project declarations in markdown or code references
    patterns = [
        r"project[:\s]+['\"]?(\w[\w\s-]+\w)",
        r"Project[:\s]+['\"]?(\w[\w\s-]+\w)",
        r"项目[:\s]+['\"]?(\w[\w\s-]+\w)",
        r"#\s*(\w[\w\s-]+\w)",  # Markdown heading might be project name
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            name = m.group(1).strip()
            if len(name) > 2 and name.lower() not in ("project", "项目", "overview", "summary"):
                return name
    return "通用"


def detect_note_types(text: str, tech_stack: dict[str, list[str]]) -> list[dict]:
    """Detect which additional note types should be created from this session.

    Returns a list of {type, ...} objects for snippet, concept, tech_card, adr.
    """
    note_types = []

    # ── Snippet detection ──
    snippets = _detect_snippets(text)
    note_types.extend(snippets)

    # ── Concept detection ──
    concepts = _detect_concepts(text, tech_stack)
    note_types.extend(concepts)

    # ── Tech Card detection ──
    tech_cards = _detect_tech_cards(text, tech_stack)
    note_types.extend(tech_cards)

    # ── ADR detection ──
    # ADRs are NOT auto-detected. Architecture decisions have fuzzy semantics
    # that require human judgment. Instead, the agent proactively asks the user
    # ("这个决策要记成 ADR 吗？") or the user explicitly triggers it
    # ("这个决定记一下"). See SKILL.md § Explicit Triggers.
    # _detect_adrs(text) is kept as a utility for the agent to call manually.

    return note_types


def _detect_snippets(text: str) -> list[dict]:
    """Detect snippet-worthy code blocks in the session."""
    snippets = []
    # Find code blocks (```...```)
    code_blocks = re.findall(r"```(\w+)?\n(.*?)```", text, re.DOTALL)
    for i, (lang, code) in enumerate(code_blocks):
        code = code.strip()
        lines = code.split("\n")
        # Snippet-worthy: ≥5 lines and not just imports/config
        if len(lines) >= 5 and not _is_boilerplate(code):
            title = _infer_snippet_title(text, code, i)
            snippets.append({
                "type": "snippet",
                "title": title,
                "language": lang or "text",
                "code": code,
                "caveats": _extract_caveats(text, code),
                "primary_tech": _infer_primary_tech(code),
            })
    return snippets[:3]  # Cap at 3 snippets


def _is_boilerplate(code: str) -> bool:
    """Check if code is mostly imports/config rather than logic."""
    boilerplate_ratio = sum(
        1 for line in code.split("\n")
        if line.strip().startswith(("import ", "from ", "#", "//", "export ", "require(", "const {", "$"))
    ) / max(len(code.split("\n")), 1)
    return boilerplate_ratio > 0.7


def _infer_snippet_title(text: str, code: str, index: int) -> str:
    """Infer a descriptive title for a snippet."""
    # Look for a comment or description right before the code block
    lines_before = text.split("```")[index * 2].strip().split("\n")
    if lines_before:
        last_line = lines_before[-1].strip()
        if len(last_line) > 5 and len(last_line) < 80:
            return last_line[:80]
    # Fallback: first comment in the code
    for line in code.split("\n"):
        stripped = line.strip()
        if stripped.startswith(("#", "//")) and len(stripped) > 5:
            return stripped.lstrip("#/ ")[:80]
    return f"Code Snippet {index + 1}"


def _extract_caveats(text: str, code: str) -> list[str]:
    """Extract caveats/warnings near the code block."""
    caveats = []
    code_start = text.find(code)
    if code_start < 0:
        return caveats
    # Look for "注意", "warning", "caveat" in nearby text (±200 chars)
    nearby = text[max(0, code_start - 200):code_start + len(code) + 200]
    for line in nearby.split("\n"):
        stripped = line.strip()
        if any(w in stripped.lower() for w in ["注意", "warning", "note:", "caveat", "小心", "don't", "必须"]):
            caveats.append(stripped[:120])
    return caveats[:5]


def _infer_primary_tech(code: str) -> str:
    """Infer the primary technology from a code block by matching known tech names."""
    for tech_list in TECH_CATEGORIES.values():
        for tech in tech_list:
            if tech.lower() in code.lower():
                return tech
    return "unknown"


def _detect_concepts(text: str, tech_stack: dict[str, list[str]]) -> list[dict]:
    """Detect new concepts being explained in the session."""
    concepts = []
    concept_techs = tech_stack.get("Concept", [])

    # Check if any concept-level tech is being explained
    for concept in concept_techs:
        concept_pattern = re.compile(
            rf"{re.escape(concept)}.*?(?:是|指的是|本质|核心|means|refers to|is a|essentially)",
            re.IGNORECASE,
        )
        if concept_pattern.search(text):
            concepts.append({
                "type": "concept",
                "name": concept,
                "core_idea": _extract_core_idea(text, concept),
                "domain": _infer_domain(text),
                "related": _find_related_concepts(text, concept, concept_techs),
            })

    # Also check for concept signals followed by explanation
    all_concept_signals = CONCEPT_SIGNALS_ZH + CONCEPT_SIGNALS_EN
    for line in text.split("\n"):
        stripped = line.strip()
        if any(sig in stripped.lower() for sig in all_concept_signals) and len(stripped) > 15:
            # Check if a known concept is nearby
            for concept_list in TECH_CATEGORIES.values():
                for tech in concept_list:
                    if tech.lower() in stripped.lower():
                        if not any(c["name"] == tech for c in concepts):
                            concepts.append({
                                "type": "concept",
                                "name": tech,
                                "core_idea": stripped[:120],
                                "domain": _infer_domain(text),
                                "related": [],
                            })

    return concepts[:3]  # Cap at 3


def _extract_core_idea(text: str, concept: str) -> str:
    """Extract the one-sentence core idea for a concept."""
    sentences = re.split(r"[。.!?\n]", text)
    for s in sentences:
        if concept.lower() in s.lower() and len(s) > 10:
            return s.strip()[:150]
    return f"Understanding of {concept}"


def _infer_domain(text: str) -> str:
    """Infer the knowledge domain from session content."""
    domains = {
        "backend": ["api", "server", "database", "endpoint", "微服务"],
        "frontend": ["ui", "component", "css", "react", "vue", "界面"],
        "devops": ["deploy", "docker", "ci", "cd", "部署"],
        "ai-ml": ["model", "training", "llm", "embedding", "模型"],
        "systems": ["process", "memory", "socket", "线程", "进程"],
    }
    lower = text.lower()
    for domain, keywords in domains.items():
        if any(kw in lower for kw in keywords):
            return domain
    return "general"


def _find_related_concepts(text: str, concept: str, all_concepts: list[str]) -> list[str]:
    """Find concepts that appear near the target concept in the text."""
    related = []
    for other in all_concepts:
        if other != concept and other.lower() in text.lower():
            # Check if they appear within 500 chars of each other
            idx_concept = text.lower().find(concept.lower())
            idx_other = text.lower().find(other.lower())
            if abs(idx_concept - idx_other) < 500:
                related.append(other)
    return related[:5]


def _detect_tech_cards(text: str, tech_stack: dict[str, list[str]]) -> list[dict]:
    """Detect technologies being used for the first time."""
    cards = []
    all_techs = []
    for category, techs in tech_stack.items():
        for tech in techs:
            all_techs.append((category, tech))

    for category, tech in all_techs:
        # Check if this appears to be first use
        is_first = any(
            sig in text.lower() for sig in FIRST_USE_SIGNALS
        ) or _is_likely_first_use(text, tech)

        cards.append({
            "type": "tech_card",
            "name": tech,
            "category": category.lower(),
            "is_first_use": is_first,
            "description": _infer_tech_description(text, tech),
            "version": _extract_version(text, tech),
            "new_pitfalls": _extract_pitfalls(text, tech),
        })

    return cards


def _is_likely_first_use(text: str, tech: str) -> bool:
    """Heuristic: tech mentioned with introductory language."""
    intro_patterns = [
        rf"(?:use|using|used|with|via|through)\s+{re.escape(tech)}",
        rf"(?:用|使用|通过)\s*{re.escape(tech)}",
        rf"{re.escape(tech)}\s*(?:is|was)\s+(?:a|the|used)",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in intro_patterns)


def _infer_tech_description(text: str, tech: str) -> str:
    """Infer a one-line description from context."""
    desc_patterns = [
        rf"{re.escape(tech)}.*?(?:是|is|a)\s+.+?[。.]",
        rf"{re.escape(tech)}.*?framework.*?[。.]",
        rf"{re.escape(tech)}.*?library.*?[。.]",
    ]
    for pat in desc_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:120]
    return f"A {tech} tool/library"


def _extract_version(text: str, tech: str) -> str | None:
    """Extract version number near a tech mention."""
    ver_pattern = rf"{re.escape(tech)}\s*[\d.]+(?:\.x)?"
    m = re.search(ver_pattern, text, re.IGNORECASE)
    if m:
        return m.group(0)
    # Look for standalone version near tech mention
    idx = text.lower().find(tech.lower())
    if idx >= 0:
        nearby = text[idx:idx + 100]
        ver_m = re.search(r"(\d+\.\d+(?:\.\d+)?(?:\.x)?)", nearby)
        if ver_m:
            return ver_m.group(1)
    return None


def _extract_pitfalls(text: str, tech: str) -> list[str]:
    """Extract issues/warnings related to a specific tech."""
    pitfalls = []
    idx = text.lower().find(tech.lower())
    if idx < 0:
        return pitfalls
    nearby = text[max(0, idx - 300):idx + 500]
    pit_sigs = ["error", "warning", "注意", "问题", "bug", "not working", "deprecated"]
    for line in nearby.split("\n"):
        stripped = line.strip()
        if any(sig in stripped.lower() for sig in pit_sigs) and len(stripped) > 10:
            pitfalls.append(stripped[:120])
    return pitfalls[:3]


def _detect_adrs(text: str) -> list[dict]:
    """Detect architecture decisions in the session."""
    adrs = []
    all_adr_signals = ARCH_SIGNALS_ZH + ARCH_SIGNALS_EN

    # Look for explicit decision patterns
    for line in text.split("\n"):
        stripped = line.strip()
        if any(sig in stripped.lower() for sig in all_adr_signals) and len(stripped) > 15:
            # Check if this mentions alternatives
            options = _extract_options(text, stripped)
            if len(options) >= 2:
                adrs.append({
                    "type": "adr",
                    "title": _infer_adr_title(stripped),
                    "background": _extract_adr_background(text, stripped),
                    "problem": stripped[:150],
                    "options": options,
                    "chosen": options[0]["name"] if options else "unknown",
                    "reasons": _extract_adr_reasons(text, stripped),
                    "tradeoffs": _extract_adr_tradeoffs(text, stripped),
                })

    return adrs[:2]  # Cap at 2 ADRs


def _extract_options(text: str, decision_line: str) -> list[dict]:
    """Extract considered alternatives from the decision context."""
    options = []
    # Look for numbered/comma-separated alternatives
    opt_patterns = [
        r"(?:方案|option|approach)\s*(\d)[:：]\s*(.+?)(?=(?:方案|option|approach)\s*\d|$)",
        r"(\d)\.\s*(.+?)(?:\s*[（(](.+?)[）)])?(?=\d\.\s|$)",
    ]
    idx = text.find(decision_line)
    if idx < 0:
        return options
    nearby = text[max(0, idx - 200):idx + len(decision_line) + 500]

    for pat in opt_patterns:
        matches = re.findall(pat, nearby, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                name = m[1].strip() if len(m) > 1 else m[0].strip()
                status = "chosen" if any(
                    s in nearby.lower() for s in ["选了", "chose", "决定", "decided"]
                ) else "considered"
                if len(name) > 3:
                    options.append({"name": name[:80], "status": status})
            else:
                if len(m) > 3:
                    options.append({"name": m.strip()[:80], "status": "considered"})

    return options[:5]


def _infer_adr_title(line: str) -> str:
    """Infer a short ADR title from a decision line."""
    # Clean up the line
    for sig in ARCH_SIGNALS_ZH + ARCH_SIGNALS_EN:
        line = line.replace(sig, "").strip()
    return line[:80] or "Architecture Decision"


def _extract_adr_background(text: str, decision_line: str) -> str:
    """Extract background context for an ADR."""
    idx = text.find(decision_line)
    if idx < 0:
        return "N/A"
    # Grab ~2 sentences before the decision
    before = text[max(0, idx - 300):idx]
    sentences = re.split(r"[。.!?\n]", before)
    context_sentences = [s.strip() for s in sentences[-3:] if len(s.strip()) > 10]
    return " ".join(context_sentences)[:200] or "N/A"


def _extract_adr_reasons(text: str, decision_line: str) -> list[str]:
    """Extract reasons for a decision."""
    reasons = []
    idx = text.find(decision_line)
    if idx < 0:
        return reasons
    nearby = text[idx:idx + len(decision_line) + 400]
    reason_sigs = ["因为", "原因", "because", "reason", "since", "考虑到", "权衡"]
    for line in nearby.split("\n"):
        stripped = line.strip()
        if any(sig in stripped.lower() for sig in reason_sigs) and len(stripped) > 10:
            reasons.append(stripped[:120])
    return reasons[:5]


def _extract_adr_tradeoffs(text: str, decision_line: str) -> list[str]:
    """Extract tradeoffs/costs of a decision."""
    tradeoffs = []
    idx = text.find(decision_line)
    if idx < 0:
        return tradeoffs
    nearby = text[idx:idx + len(decision_line) + 500]
    trade_sigs = ["代价", "缺点", "不足", "tradeoff", "downside", "cost", "drawback", "但是", "不过", "however"]
    for line in nearby.split("\n"):
        stripped = line.strip()
        if any(sig in stripped.lower() for sig in trade_sigs) and len(stripped) > 10:
            tradeoffs.append(stripped[:120])
    return tradeoffs[:5]


def extract(text: str, timestamp: str | None = None) -> dict:
    """Main extraction function. Returns structured knowledge JSON."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    tech_stack = detect_tech_stack(text)
    problems = detect_problems(text)
    changes = detect_changes(text)
    note_types = detect_note_types(text, tech_stack)

    return {
        "session_topic": _summarize_topic(text),
        "project_name": infer_project_name(text),
        "summary": _summarize(text),
        "tech_stack": tech_stack,
        "changes": changes,
        "problems_solved": problems,
        "open_issues": _detect_open_issues(text),
        "next_actions": _detect_next_actions(text),
        "note_types": note_types,
        "timestamp": timestamp,
    }


def _summarize_topic(text: str) -> str:
    """Produce a one-line session topic."""
    # Return first substantive line that isn't a greeting
    for line in text.split("\n"):
        stripped = line.strip()
        if len(stripped) > 10 and not stripped.startswith(("#", ">", "```", "User:", "AI:")):
            return stripped[:100]
    return "Session"


def _summarize(text: str) -> str:
    """Produce a brief (≤3 sentence) summary."""
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
    if not lines:
        return "No summary available."
    # Heuristic: pick the first 2-3 substantive lines
    summary_lines = lines[:3]
    return " ".join(summary_lines)[:300]


def _detect_open_issues(text: str) -> list[str]:
    """Detect unresolved items or next-step blockers."""
    issues = []
    sig_zh = ["未解决", "还没", "待解决", "下一步", "TODO", "FIXME"]
    sig_en = ["TODO", "FIXME", "not yet", "pending", "unresolved", "next step"]
    for line in text.split("\n"):
        stripped = line.strip()
        if any(sig in stripped for sig in sig_zh + sig_en):
            issues.append(stripped[:120])
    return issues[:5]


def _detect_next_actions(text: str) -> list[str]:
    """Detect planned next actions."""
    actions = []
    sig_zh = ["下一步", "接下来", "计划", "准备"]
    sig_en = ["next step", "plan to", "going to", "will add", "will implement"]
    for line in text.split("\n"):
        stripped = line.strip()
        if any(sig in stripped for sig in sig_zh + sig_en):
            actions.append(stripped[:120])
    return actions[:5]


def main():
    text = None
    output_path = None

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
        else:
            i += 1

    # Read from stdin if no --session-text provided
    if text is None:
        text = sys.stdin.read()

    if not text.strip():
        print(json.dumps({"error": "No input text provided"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    result = extract(text)

    json_output = json.dumps(result, ensure_ascii=False, indent=2)

    if output_path:
        Path(output_path).write_text(json_output + "\n", encoding="utf-8")
        print(f"Extracted knowledge written to {output_path}")
    else:
        print(json_output)


if __name__ == "__main__":
    main()
