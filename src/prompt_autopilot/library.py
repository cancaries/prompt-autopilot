"""
Prompt Library - Store, search, and reuse optimized prompts.

Based on PromptHive patterns:
- ph use essentials/commit
- git diff | ph use essentials/commit | claude

Library structure:
~/.prompt-autopilot/library/
├── login.md
├── sorting.md
├── _index.json
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from .core import AUTOPILOT_DIR

# Library paths
LIBRARY_DIR = AUTOPILOT_DIR / "library"
LIBRARY_INDEX = LIBRARY_DIR / "_index.json"

LIBRARY_DIR.mkdir(exist_ok=True)


# =============================================================================
# Storage
# =============================================================================

def _load_index() -> dict:
    if LIBRARY_INDEX.exists():
        with open(LIBRARY_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"prompts": {}, "tags": []}


def _save_index(index: dict):
    with open(LIBRARY_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def _index_add(name: str, tags: list[str]):
    index = _load_index()
    index["prompts"][name] = {"tags": tags, "name": name}
    for tag in tags:
        if tag not in index["tags"]:
            index["tags"].append(tag)
    _save_index(index)


def _index_remove(name: str):
    index = _load_index()
    if name in index["prompts"]:
        del index["prompts"][name]
        # Rebuild tags
        all_tags = set()
        for p in index["prompts"].values():
            all_tags.update(p.get("tags", []))
        index["tags"] = sorted(all_tags)
        _save_index(index)


def _index_update_usage(name: str, delta: int = 1):
    index = _load_index()
    if name in index["prompts"]:
        index["prompts"][name]["usage_count"] = (
            index["prompts"][name].get("usage_count", 0) + delta
        )
        _save_index(index)


# =============================================================================
# Frontmatter parsing
# =============================================================================

def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content. Returns (metadata, body)."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    fm_text = match.group(1)
    body = match.group(2)
    meta = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                # Parse list
                items = [x.strip() for x in val[1:-1].split(",")]
                val = [x for x in items if x]
            elif val.isdigit():
                val = int(val)
            elif val.replace(".", "", 1).isdigit():
                val = float(val)
            meta[key] = val
    return meta, body


def _format_frontmatter(meta: dict, body: str) -> str:
    """Format metadata and body as markdown with frontmatter."""
    lines = ["---"]
    for key, val in meta.items():
        if isinstance(val, list):
            lines.append(f"{key}: [{', '.join(val)}]")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body


# =============================================================================
# CRUD Operations
# =============================================================================

def save_prompt(
    name: str,
    prompt: str,
    tags: Optional[list[str]] = None,
    description: Optional[str] = None,
    force: bool = False,
) -> dict:
    """
    Save an optimized prompt to the library.

    Args:
        name: unique name (slug)
        prompt: the prompt content
        tags: optional tags for search
        description: optional description
        force: overwrite if exists

    Returns:
        saved prompt metadata
    """
    safe_name = _slugify(name)
    path = LIBRARY_DIR / f"{safe_name}.md"

    if path.exists() and not force:
        raise FileExistsError(f"Prompt '{safe_name}' already exists. Use --force to overwrite.")

    meta = {
        "name": safe_name,
        "tags": tags or [],
        "created": datetime.now().date().isoformat(),
        "updated": datetime.now().date().isoformat(),
        "usage_count": 0,
    }
    if description:
        meta["description"] = description

    content = _format_frontmatter(meta, prompt)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    _index_add(safe_name, tags or [])
    return meta


def load_prompt(name: str) -> Optional[dict]:
    """Load a prompt by name. Returns None if not found."""
    safe_name = _slugify(name)
    path = LIBRARY_DIR / f"{safe_name}.md"
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    meta, body = _parse_frontmatter(content)
    meta["content"] = body
    return meta


def update_prompt(name: str, prompt: Optional[str] = None, tags: Optional[list[str]] = None,
                  description: Optional[str] = None) -> Optional[dict]:
    """Update an existing prompt. Returns updated metadata or None if not found."""
    safe_name = _slugify(name)
    path = LIBRARY_DIR / f"{safe_name}.md"
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    meta, body = _parse_frontmatter(content)
    body_content = body.strip() if body else ""
    if prompt is not None:
        body_content = prompt
    if tags is not None:
        meta["tags"] = tags
    if description is not None:
        meta["description"] = description
    meta["updated"] = datetime.now().date().isoformat()

    new_content = _format_frontmatter(meta, body_content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    _index_add(safe_name, meta.get("tags", []))
    return {**meta, "content": body_content}


def delete_prompt(name: str) -> bool:
    """Delete a prompt. Returns True if deleted, False if not found."""
    safe_name = _slugify(name)
    path = LIBRARY_DIR / f"{safe_name}.md"
    if not path.exists():
        return False
    path.unlink()
    _index_remove(safe_name)
    return True


def list_prompts() -> list[dict]:
    """List all prompts sorted by usage_count descending."""
    index = _load_index()
    result = []
    for name in index["prompts"]:
        prompt = load_prompt(name)
        if prompt:
            result.append(prompt)
    return sorted(result, key=lambda p: p.get("usage_count", 0), reverse=True)


def search_prompts(query: str) -> list[dict]:
    """Search prompts by name, tags, or content."""
    query_lower = query.lower()
    results = []
    for prompt in list_prompts():
        name = prompt.get("name", "").lower()
        tags = [t.lower() for t in prompt.get("tags", [])]
        content = prompt.get("content", "").lower()
        description = prompt.get("description", "").lower()

        if (query_lower in name or
            query_lower in content or
            query_lower in description or
            any(query_lower in tag for tag in tags)):
            results.append(prompt)
    return results


def use_prompt(name: str, instruction_override: str) -> Optional[dict]:
    """
    Use a template and apply a new instruction override.
    Increments usage_count.
    """
    safe_name = _slugify(name)
    prompt = load_prompt(safe_name)
    if not prompt:
        return None

    # Apply instruction override
    content = prompt.get("content", "")
    if instruction_override:
        # Replace first [TASK] placeholder or append instruction
        if "[TASK]" in content or "[任务]" in content:
            content = re.sub(r"\[TASK\]|\[任务\]", instruction_override, content, count=1)
        else:
            # Append to end
            content = f"{content}\n\n## 新任务\n{instruction_override}"

    # Increment usage
    _index_update_usage(safe_name, 1)
    _update_usage_count_in_file(safe_name, 1)

    return {
        **prompt,
        "content": content,
        "instruction_override": instruction_override,
    }


def _update_usage_count_in_file(name: str, delta: int):
    path = LIBRARY_DIR / f"{name}.md"
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    meta, body = _parse_frontmatter(content)
    current = meta.get("usage_count", 0)
    if isinstance(current, str):
        current = int(current) if current.isdigit() else 0
    meta["usage_count"] = current + delta
    meta["updated"] = datetime.now().date().isoformat()
    new_content = _format_frontmatter(meta, body)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)


# =============================================================================
# Smart Recommendation
# =============================================================================

def find_similar(task: str, top_k: int = 3) -> list[tuple[dict, float]]:
    """
    Find similar prompts based on keyword + tag matching.
    Returns list of (prompt, similarity_score) sorted by score descending.
    Score is 0-100.
    """
    task_lower = task.lower()
    task_words = set(task_lower.split())

    # Chinese keyword expansion
    expansions = {
        "登录": ["auth", "login", "登陆", "认证", "jwt", "session", "用户", "password"],
        "注册": ["register", "signup", "账号", "account"],
        "排序": ["sort", "quicksort", "mergesort", "堆排序", "快速排序"],
        "api": ["接口", "endpoint", "rest", "http", "json"],
        "数据库": ["db", "sql", "增删改查", "crud", "mysql", "postgresql"],
        "缓存": ["cache", "lru", "redis", "memcached"],
        "链表": ["linked list", "list"],
        "树": ["tree", "bst", "二叉树", "二叉搜索树"],
        "图": ["graph", "最短路径", "dijkstra", "bfs", "dfs"],
        "栈": ["stack", "队列", "queue"],
        "字符串": ["string", "字符串", "正则", "regex"],
        "动态规划": ["dp", "fibonacci", "斐波那契", "爬楼梯"],
        "邮件": ["email", "mail", "letter"],
        "解释": ["explain", "解释", "说明", "是什么"],
        "文章": ["article", "blog", "写作", "writing"],
    }

    expanded_words = set(task_words)
    for kw, syns in expansions.items():
        if kw in task_lower:
            expanded_words.update(syns)

    all_prompts = list_prompts()
    scored = []

    for prompt in all_prompts:
        score = 0
        name = prompt.get("name", "").lower()
        tags = [t.lower() for t in prompt.get("tags", [])]
        content = prompt.get("content", "").lower()

        # Name match: high weight
        name_words = set(name.replace("-", " ").replace("_", " ").split())
        name_overlap = len(expanded_words & name_words)
        score += name_overlap * 20

        # Tag match: medium weight
        tag_overlap = len(set(expanded_words) & set(tags))
        score += tag_overlap * 15

        # Content keyword match
        content_words = set(content.split())
        content_overlap = len(expanded_words & content_words)
        score += min(content_overlap * 2, 30)

        # Exact phrase match
        if task_lower[:10] in content or task_lower[:10] in name:
            score += 10

        if score > 0:
            scored.append((prompt, min(score, 100)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


# =============================================================================
# Utilities
# =============================================================================

def _slugify(name: str) -> str:
    """Convert name to a safe filename slug."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\-]", "-", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-")
    return name or "untitled"


def import_existing_templates() -> int:
    """
    Import any existing JSON templates from TEMPLATES_DIR into the new library.
    Returns count of imported templates.
    """
    from .core import TEMPLATES_DIR
    imported = 0
    for filepath in TEMPLATES_DIR.glob("*.json"):
        with open(filepath, "r", encoding="utf-8") as f:
            template = json.load(f)
        try:
            save_prompt(
                name=template.get("name", filepath.stem),
                prompt=template.get("prompt", ""),
                tags=template.get("tags", []),
                description=template.get("description", ""),
                force=True,
            )
            imported += 1
        except Exception:
            pass
    return imported
