#!/usr/bin/env python3
"""Structural self-check for a flow-brief artifact.

Zero dependencies: Python 3.8+ standard library only.

Exit codes are three-valued and never collapse into each other:
    0  pass
    1  fail        - at least one ERROR
    2  unverified  - could not run a check it was asked to run
                     (e.g. --visual requested but Node or Chrome missing)

"Unverified" is NOT a pass. A tool that reports 0 when it did not actually
check anything is worse than one that fails, because it trains everyone to
trust a green that means nothing.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

ERROR, WARN = "ERROR", "WARN"


class Finding:
    __slots__ = ("level", "check", "message", "hint")

    def __init__(self, level: str, check: str, message: str, hint: str = "") -> None:
        self.level, self.check, self.message, self.hint = level, check, message, hint

    def render(self) -> str:
        head = f"  [{self.level:5}] {self.check}: {self.message}"
        return head + (f"\n           → {self.hint}" if self.hint else "")


class TagBalance(HTMLParser):
    """Track unclosed / stray-closed tags with line numbers."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.unclosed: list[tuple[str, int]] = []
        self.stray: list[tuple[str, int]] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                # everything above it was never closed
                self.unclosed.extend(self.stack[i + 1:])
                del self.stack[i:]
                return
        self.stray.append((tag, self.getpos()[0]))

    def finish(self):
        self.unclosed.extend(self.stack)
        self.stack = []


def strip_style_and_script(html: str) -> str:
    out = re.sub(r"<style\b.*?</style>", "", html, flags=re.S | re.I)
    return re.sub(r"<script\b.*?</script>", "", out, flags=re.S | re.I)


def strip_data_uris(html: str) -> str:
    """Base64 payloads are megabytes of noise for every text-level check.

    The replacement must contain no angle brackets: a '>' here would truncate the
    enclosing tag for every downstream regex that matches `<img\\b[^>]*>`.
    """
    return re.sub(r"data:[a-zA-Z0-9.+/-]+;base64,[A-Za-z0-9+/=]*", "data:BASE64", html)


# --------------------------------------------------------------------------
# individual checks — each returns a list of Finding
# --------------------------------------------------------------------------

def check_tag_balance(html: str) -> list[Finding]:
    p = TagBalance()
    try:
        p.feed(html)
        p.finish()
    except Exception as exc:  # pragma: no cover - parser blowup is itself a finding
        return [Finding(ERROR, "tag-balance", f"HTML parser failed: {exc}")]
    out = []
    for tag, line in p.unclosed[:10]:
        out.append(Finding(ERROR, "tag-balance", f"<{tag}> opened at line {line} is never closed"))
    for tag, line in p.stray[:10]:
        out.append(Finding(ERROR, "tag-balance", f"</{tag}> at line {line} closes nothing"))
    return out


def check_markdown_leak(html: str) -> list[Finding]:
    body = strip_data_uris(strip_style_and_script(html))
    out = []
    hits = [m.start() for m in re.finditer(r"\*\*", body)]
    if hits:
        line = body[: hits[0]].count("\n") + 1
        out.append(Finding(
            ERROR, "markdown-leak",
            f"{len(hits)} occurrence(s) of '**' in HTML content (first near line {line})",
            "Markdown bold does not render in HTML. Use <b>...</b>.",
        ))
    for token, name in ((r"(?<!`)\[[^\]\n]{1,60}\]\([^)\n]{1,120}\)", "markdown link"),):
        if re.search(token, body):
            out.append(Finding(WARN, "markdown-leak", f"possible {name} syntax in HTML content"))
    return out


def check_placeholders(html: str) -> list[Finding]:
    # Deliberately NOT stripping data URIs here: "base64,PLACEHOLDER" is itself
    # one of the placeholders we must catch.
    body = html
    out = []
    literal = [
        "PLACEHOLDER", "__TITLE__", "TODO:", "Lorem ipsum",
        "A finding, not a topic", "Thing A", "Thing B",
        "what it owns", "Anticipated question",
    ]
    for token in literal:
        n = body.count(token)
        if n:
            out.append(Finding(
                ERROR, "placeholder",
                f"template placeholder still present: {token!r} ({n}x)",
                "Replace every skeleton placeholder with real content.",
            ))
    # a lone ellipsis cell is the skeleton's filler
    fillers = len(re.findall(r">\s*…\s*<", body))
    if fillers:
        out.append(Finding(
            ERROR, "placeholder",
            f"{fillers} cell(s) still contain only the filler ellipsis",
        ))
    return out


def check_theme(html: str) -> list[Finding]:
    style = "\n".join(re.findall(r"<style\b.*?</style>", html, flags=re.S | re.I))
    if not style:
        return [Finding(ERROR, "theme", "no <style> block found")]
    out = []
    has_root = re.search(r":root\s*\{", style)
    has_media = re.search(r"@media\s*\([^)]*prefers-color-scheme\s*:\s*dark", style)
    has_attr = re.search(r':root\s*\[\s*data-theme\s*=\s*["\']?dark', style)
    if not has_root:
        out.append(Finding(ERROR, "theme", "no bare :root block (the light/default palette)"))
    if not has_media:
        out.append(Finding(ERROR, "theme", "no prefers-color-scheme:dark block (system-dark readers)"))
    if not has_attr:
        out.append(Finding(ERROR, "theme", 'no :root[data-theme="dark"] block (explicit toggle)'))
    if has_media and not re.search(r"prefers-color-scheme\s*:\s*dark[^{]*\{\s*:root:not\(", style):
        out.append(Finding(
            WARN, "theme",
            "dark media query does not guard with :root:not([data-theme=\"light\"])",
            "Without the guard an explicit light choice loses to a dark OS.",
        ))
    if not re.search(r"body\s*\{[^}]*background", style):
        out.append(Finding(
            ERROR, "theme", "body has no explicit background",
            "A transparent body borrows the host page's ground and can render unreadably.",
        ))
    return out


class _ImgContext(HTMLParser):
    """Record each <img> together with the classes of its open ancestors.

    A naive rfind("<div class=...") vs rfind("</div>") test gets this wrong the
    moment the image has an older sibling div, which is the common case.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.images: list[tuple[int, dict, tuple[str, ...]]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "img":
            self.images.append((self.getpos()[0], a, tuple(self.stack)))
            return
        if tag not in VOID:
            self.stack.append(a.get("class") or "")

    def handle_startendtag(self, tag, attrs):
        if tag == "img":
            self.images.append((self.getpos()[0], dict(attrs), tuple(self.stack)))

    def handle_endtag(self, tag):
        if tag not in VOID and self.stack:
            self.stack.pop()


def check_images(html: str) -> list[Finding]:
    out = []
    body = strip_data_uris(html)
    p = _ImgContext()
    try:
        p.feed(body)
    except Exception as exc:
        return [Finding(WARN, "image", f"could not parse image context: {exc}")]

    for line, attrs, ancestors in p.images:
        if "alt" not in attrs:
            out.append(Finding(WARN, "image", f"<img> at line {line} has no alt text"))
        classes = " ".join(ancestors)
        contained = "shot" in classes.split() or "box" in classes.split()
        inline_w = "width:100%" in (attrs.get("style") or "").replace(" ", "")
        if not (contained or inline_w):
            out.append(Finding(
                ERROR, "image",
                f"<img> at line {line} is outside .shot/.box and sets no width",
                "An unconstrained image can push the page sideways.",
            ))

    # The .shot spotlight only works if the image fills its container. That is a
    # stylesheet guarantee, not something every image should repeat inline.
    if '<div class="shot"' in body:
        style = "\n".join(re.findall(r"<style\b.*?</style>", html, flags=re.S | re.I))
        rule = re.search(r"\.shot\s+img\s*\{([^}]*)\}", style)
        if not rule or "width:100%" not in rule.group(1).replace(" ", ""):
            out.append(Finding(
                ERROR, "image",
                ".shot is used but the stylesheet has no '.shot img{width:100%}' rule",
                "A narrower image lets the .mark spotlight tint the leftover strip grey.",
            ))
    return out


def check_provenance(html: str) -> list[Finding]:
    """Rule 3 — every box label carries at least one provenance pill."""
    out = []
    labels = list(re.finditer(r'<div class="lbl"[^>]*>(.*?)</div>', html, flags=re.S))
    if not labels:
        return [Finding(
            ERROR, "provenance", "no in/out boxes at all — nothing to attribute",
            "An artifact with no .box has not been written yet. Absence is a failure "
            "here, not an exemption: otherwise an empty file outscores a half-finished one.")]
    bare = 0
    for m in labels:
        if "pill" not in m.group(1):
            bare += 1
    if bare:
        out.append(Finding(
            ERROR, "provenance",
            f"{bare} of {len(labels)} box label(s) carry no provenance pill",
            "Rule 3: every factual cell states its rung "
            "(real / plan / gap), or you cannot tell intent from reality.",
        ))
    return out


def check_dflow(html: str) -> list[Finding]:
    """Rule 2 — every band ends with a three-cell data-flow strip."""
    out = []
    bands = len(re.findall(r'<div class="band[^"]*"', html))
    strips = re.findall(r'<div class="dflow"[^>]*>(.*?)</div>\s*</div>', html, flags=re.S)
    if bands == 0:
        return [Finding(
            ERROR, "node-triad", "no step bands at all — there is no flow on this page",
            "A flow brief without bands is an empty shell. This check measures whether the "
            "work was done, not merely whether what exists is well-formed.")]
    if len(strips) < bands:
        out.append(Finding(
            ERROR, "node-triad",
            f"{bands} band(s) but only {len(strips)} .dflow strip(s)",
            "Rule 2: every band answers upstream / produced / picked-up.",
        ))
    for i, s in enumerate(strips):
        n = len(re.findall(r"<i>", s))
        if n != 3:
            out.append(Finding(
                ERROR, "node-triad",
                f".dflow #{i + 1} has {n} labelled cell(s), expected exactly 3",
            ))
    return out


def check_show_the_gap(html: str) -> list[Finding]:
    """Rule 5 — the page must name at least one thing that does not work."""
    if re.search(r'class="pill gap"', html) or re.search(r'class="note warn"', html):
        return []
    return [Finding(
        ERROR, "show-the-gap",
        "no .pill.gap and no .note.warn anywhere on the page",
        "Rule 5: a page with only success paths reads as marketing. "
        "If you truly found no gap, the collection was probably too shallow.",
    )]


def check_tables(html: str) -> list[Finding]:
    out = []
    total = len(re.findall(r"<table\b", html, flags=re.I))
    wrapped = len(re.findall(r'<div class="tw">\s*<table\b', html, flags=re.I))
    if total != wrapped:
        out.append(Finding(
            ERROR, "overflow",
            f"{total - wrapped} of {total} table(s) not wrapped in .tw",
            "Unwrapped wide tables push the whole page sideways.",
        ))
    return out


def check_anti_cheat(html: str) -> list[Finding]:
    style = "\n".join(re.findall(r"<style\b.*?</style>", html, flags=re.S | re.I))
    out = []
    for sel in ("body", "html", r"\.wrap", "section"):
        pat = rf"(^|\}}|,)\s*{sel}\s*(,[^{{]*)?\{{[^}}]*overflow(-x)?\s*:\s*hidden"
        if re.search(pat, style, flags=re.M):
            out.append(Finding(
                ERROR, "anti-cheat",
                f"overflow:hidden on '{sel.replace(chr(92), '')}'",
                "Hiding overflow conceals a layout defect instead of fixing it. "
                "Wide content belongs in a .tw scroll container.",
            ))
    return out


def check_lane_consistency(html: str) -> list[Finding]:
    out = []
    for i, m in enumerate(re.finditer(r'<div class="flow">(.*?)(?=<section|</section)', html, flags=re.S), 1):
        block = m.group(1)
        lanes = len(re.findall(r"<span></span>", block.split("</div>")[0] + "</div>"))
        heads = re.search(r'<div class="lanehd">(.*?)</div>\s*(?=<!--|<div class="band)', block, flags=re.S)
        n_head = len(re.findall(r"<div>", heads.group(1))) if heads else 0
        if n_head and not (4 <= n_head <= 6):
            out.append(Finding(
                WARN, "lanes",
                f"swimlane #{i} has {n_head} lanes (recommended 4–6)",
                "Under 4 a swimlane adds nothing over a list; over 6 the columns are unreadable.",
            ))
        if lanes and n_head and lanes != n_head:
            out.append(Finding(
                ERROR, "lanes",
                f"swimlane #{i}: {lanes} guide line(s) but {n_head} lane header(s)",
            ))
        bands = len(re.findall(r'<div class="band', block))
        if bands and not (6 <= bands <= 16):
            out.append(Finding(
                WARN, "lanes",
                f"swimlane #{i} has {bands} bands; 8–14 is the recommended range, "
                f"and this warning fires outside 6–16",
            ))
    return out


def check_code_fact_precision(html: str) -> list[Finding]:
    """A code-fact claim is only checkable if it says *where*.

    Naming the file is not enough — a reader who wants to verify "the script
    never writes" needs the line, or they have to read the whole file. Two of
    three trial runs did this unprompted; the third named files nine times
    without a single line number, which is what this check is for.
    """
    body = strip_data_uris(strip_style_and_script(html))
    files = set(re.findall(r"[\w./-]+\.(?:py|mjs|js|ts|tsx|go|rs|java|rb|php|cs|kt|swift|c|cpp|h)", body))
    if not files:
        return []
    with_line = re.findall(r"[\w./-]+\.(?:py|mjs|js|ts|tsx|go|rs|java|rb|php|cs|kt|swift|c|cpp|h):\d+", body)
    if not with_line:
        return [Finding(
            WARN, "code-fact",
            f"{len(files)} source file(s) cited, none with a line number",
            "Rule 3 asks code facts to carry `file:line`. Without the line the reader "
            "cannot check the claim in ten seconds, which is the whole point of the rung.",
        )]
    return []

CHECKS = [
    ("tag-balance", check_tag_balance),
    ("markdown-leak", check_markdown_leak),
    ("placeholder", check_placeholders),
    ("theme", check_theme),
    ("image", check_images),
    ("provenance", check_provenance),
    ("node-triad", check_dflow),
    ("show-the-gap", check_show_the_gap),
    ("overflow", check_tables),
    ("anti-cheat", check_anti_cheat),
    ("lanes", check_lane_consistency),
    ("code-fact", check_code_fact_precision),
]


def run_visual(path: Path) -> tuple[int, str]:
    """Delegate to the optional Node checker. Returns (exit_code, text)."""
    script = Path(__file__).with_name("check_visual.mjs")
    if not script.exists():
        return 2, f"visual: check_visual.mjs not found next to {Path(__file__).name}"
    if shutil.which("node") is None:
        return 2, "visual: node not on PATH — visual dimension UNVERIFIED (not passed)"
    try:
        proc = subprocess.run(
            ["node", str(script), str(path)],
            capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        return 2, "visual: checker timed out — UNVERIFIED"
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Structural self-check for a flow-brief artifact.")
    ap.add_argument("path", type=Path)
    ap.add_argument("--visual", action="store_true",
                    help="also run the optional Node/Chrome viewport check")
    args = ap.parse_args()

    if not args.path.exists():
        print(f"file not found: {args.path}", file=sys.stderr)
        return 2
    html = args.path.read_text(encoding="utf-8", errors="replace")

    findings: list[Finding] = []
    for _name, fn in CHECKS:
        try:
            findings.extend(fn(html))
        except Exception as exc:  # a broken check must not masquerade as a pass
            findings.append(Finding(ERROR, _name, f"check itself failed: {exc}"))

    errors = [f for f in findings if f.level == ERROR]
    warns = [f for f in findings if f.level == WARN]

    size_kb = len(html.encode("utf-8")) // 1024
    print(f"flow-brief check · {args.path.name} · {size_kb} KB")
    print(f"  checks run: {len(CHECKS)}   errors: {len(errors)}   warnings: {len(warns)}")
    if findings:
        print()
        for f in findings:
            print(f.render())

    code = 1 if errors else 0

    if args.visual:
        print()
        vcode, vtext = run_visual(args.path)
        print(vtext or "(no output)")
        if vcode == 2:
            print("\n  visual dimension UNVERIFIED — report it as such, never as passed.")
            code = max(code, 2) if code != 1 else 1
        elif vcode != 0:
            code = 1
    else:
        print("\n  note: structural checks only. Horizontal overflow and theme rendering "
              "are NOT covered — rerun with --visual before calling the artifact complete.")

    print()
    print({0: "RESULT: pass", 1: "RESULT: fail", 2: "RESULT: unverified"}[code])
    return code


if __name__ == "__main__":
    sys.exit(main())
