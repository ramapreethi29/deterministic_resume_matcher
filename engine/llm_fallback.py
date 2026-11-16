"""LLM fallback for JD bullets the skill dictionary could not resolve.

Rules this module enforces:
  * It is called ONLY for bullets with zero dictionary hits.
  * One bullet per call, temperature 0, schema-constrained JSON output.
  * Every term the model returns must pass validate_terms() (grounded in the
    bullet, not a stop word, not already known, short).
  * The LLM never decides a match or a score. If it fails, the analysis goes on
    and the result carries a warning.
"""
from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Protocol

MODEL = "qwen2.5:7b"
PROMPT_VERSION = "v1"          # bump when SYSTEM/EXAMPLES change (invalidates cache)
MAX_BULLET_CHARS = 400
MAX_TERM_WORDS = 4

SCHEMA = {
    "type": "object",
    "properties": {"skills": {"type": "array", "items": {"type": "string"}}},
    "required": ["skills"],
}

SYSTEM = (
    "Extract only technical skills, tools, frameworks, libraries, protocols or "
    "technical concepts from the sentence. Copy each term exactly as written in "
    'the sentence. Return JSON {"skills": []}. If there are none, return '
    '{"skills": []}. Do not explain.'
)
EXAMPLES = [
    ("Experience building scalable microservices with gRPC",
     {"skills": ["microservices", "grpc"]}),
    ("Ability to work in a fast-paced environment", {"skills": []}),
    ("Hands-on with Terraform and Ansible for provisioning",
     {"skills": ["terraform", "ansible"]}),
]

STOP = {
    "experience", "knowledge", "understanding", "familiarity", "skills", "skill",
    "team", "ability", "strong", "basic", "good", "work", "environment",
    "communication", "teamwork", "development", "software", "technology",
    "technologies", "tools", "applications", "application", "systems", "system",
}


class ChatClient(Protocol):
    def chat(self, *, model: str, messages: list, format: dict, options: dict) -> Mapping: ...


@dataclass
class LLMSkill:
    term: str
    bullet_id: int
    bullet: str
    grounded: bool = True
    source: str = "llm"


@dataclass
class LLMResult:
    items: list[LLMSkill] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    calls: int = 0
    cache_hits: int = 0

    @property
    def terms(self) -> list[str]:
        return sorted({i.term for i in self.items})


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def validate_terms(
    candidates: Iterable[str],
    bullet: str,
    known_terms: set[str],
    canon: Callable[[str], str] = lambda s: s,
) -> list[str]:
    """Keep only terms that are grounded in the bullet and genuinely new."""
    bullet_l = bullet.lower()
    out: set[str] = set()
    for raw in candidates:
        if not isinstance(raw, str):
            continue
        t = canon(raw.strip().lower())
        if not t or t in STOP:
            continue
        if len(t.split()) > MAX_TERM_WORDS:
            continue
        if raw.strip().lower() not in bullet_l and t not in bullet_l:
            continue                                  # not grounded -> hallucination
        if t in known_terms:
            continue                                  # dictionary already covers it
        out.add(t)
    return sorted(out)


def _parse(content: str) -> list[str] | None:
    """Parse and schema-check the model output; None means invalid."""
    try:
        data = json.loads(content)
    except (TypeError, ValueError):
        return None
    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
        return None
    return skills


# --------------------------------------------------------------------------- #
# model call (timeout + one retry)
# --------------------------------------------------------------------------- #
def _messages(bullet: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM}]
    for q, a in EXAMPLES:
        msgs += [{"role": "user", "content": q},
                 {"role": "assistant", "content": json.dumps(a)}]
    msgs.append({"role": "user", "content": bullet})
    return msgs


def _default_client(host: str | None = None) -> ChatClient:
    import ollama                                     # lazy: tests need no ollama
    return ollama.Client(host=host) if host else ollama.Client()


def _call_once(client: ChatClient, bullet: str, timeout_s: float) -> list[str] | None:
    pool = ThreadPoolExecutor(max_workers=1)
    fut = pool.submit(
        client.chat, model=MODEL, messages=_messages(bullet),
        format=SCHEMA, options={"temperature": 0},
    )
    try:
        resp = fut.result(timeout=timeout_s)
        return _parse(resp["message"]["content"])
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


class LLMUnavailable(Exception):
    pass


def _extract_bullet(client: ChatClient, bullet: str, timeout_s: float) -> list[str]:
    for _ in range(2):                                # first try + one retry
        try:
            parsed = _call_once(client, bullet, timeout_s)
        except FutureTimeout as e:
            raise LLMUnavailable("timeout") from e
        except Exception as e:                        # connection refused, model missing...
            raise LLMUnavailable(type(e).__name__) from e
        if parsed is not None:
            return parsed
    return []                                         # invalid JSON twice -> nothing


# --------------------------------------------------------------------------- #
# cache + review log
# --------------------------------------------------------------------------- #
def _key(bullet: str) -> str:
    return hashlib.sha256(f"{MODEL}|{PROMPT_VERSION}|{bullet}".encode()).hexdigest()


def _load_cache(path: Path | None) -> dict:
    if path and path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def _save_cache(path: Path | None, cache: dict) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, indent=0), encoding="utf-8")


def _log_terms(path: Path | None, items: list[LLMSkill], jd_title: str | None) -> None:
    """Append accepted terms for weekly review. Terms and bullets only, no resume data."""
    if not path or not items:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for i in items:
            f.write(json.dumps({"term": i.term, "bullet": i.bullet,
                                "jd_title": jd_title}) + "\n")


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def extract_unresolved(
    bullets: Iterable[str],
    known_terms: set[str],
    canon: Callable[[str], str] = lambda s: s,
    *,
    client: ChatClient | None = None,
    timeout_s: float = 10.0,
    cache_path: Path | None = None,
    log_path: Path | None = None,
    jd_title: str | None = None,
) -> LLMResult:
    """Run the LLM on unresolved bullets and return validated terms.

    known_terms: every canonical skill name AND alias already in the dictionary.
    """
    result = LLMResult()
    todo = [(i, b.strip()) for i, b in enumerate(bullets)
            if b and b.strip() and len(b.strip()) <= MAX_BULLET_CHARS]
    if not todo:
        return result

    cache = _load_cache(cache_path)
    dirty = False
    unavailable = False

    for idx, bullet in todo:
        k = _key(bullet)
        if k in cache:
            raw_terms = cache[k]
            result.cache_hits += 1
        elif unavailable:
            continue
        else:
            try:
                client = client or _default_client()
                raw_terms = _extract_bullet(client, bullet, timeout_s)
                result.calls += 1
            except LLMUnavailable as e:
                unavailable = True                    # circuit breaker: stop calling
                result.warnings.append(
                    f"LLM fallback unavailable ({e}); skipped unresolved bullets.")
                continue
            except Exception as e:                    # e.g. ollama not installed
                unavailable = True
                result.warnings.append(f"LLM fallback unavailable ({type(e).__name__}).")
                continue
            cache[k] = raw_terms
            dirty = True

        for t in validate_terms(raw_terms, bullet, known_terms, canon):
            result.items.append(LLMSkill(term=t, bullet_id=idx, bullet=bullet))

    if dirty:
        _save_cache(cache_path, cache)
    _log_terms(log_path, result.items, jd_title)
    return result


def literal_match(
    term: str,
    sections: Mapping[str, str],
    skip_sections: frozenset[str] = frozenset(
        {"personal_info", "interests", "references", "declaration", "languages"}),
) -> list[str]:
    """Sections of the resume that contain `term` as a whole phrase."""
    rx = re.compile(rf"(?<![\w.+#]){re.escape(term)}(?![\w.+#])", re.I)
    return [name for name, text in sections.items()
            if name not in skip_sections and isinstance(text, str) and rx.search(text)]
