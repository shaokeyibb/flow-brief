---
name: flow-brief
description: 'Produce a single-file HTML swimlane brief that walks a system, module, or upcoming feature past a non-specialist reader, with provenance badges that separate what is measured from what is merely intended. Use this whenever someone needs to explain how something works to people outside the team — a flow diagram, an architecture walkthrough, an onboarding page, a design-review handout, a 介绍图 or 泳道图 — and especially when they describe the need without naming a format: "explain this to my boss", "draw how the data moves", "something the new hire can read", "I have to present this next week".'
---

# Flow Brief

Produce one self-contained `.html` file: a swimlane walkthrough that explains a system,
a module, or an upcoming feature to someone who does not work inside it. No build step,
no assets beyond one Google Fonts link, opens by double-click.

Match every reader-facing string to the language of the user's request (a Chinese request
gets a Chinese page). Keep identifiers, file paths, commands, and error codes verbatim.

**The reader is not your peer.** A flow brief a fellow engineer enjoys is usually one a
director abandons after three lines. Everything below exists to prevent that.

## Fast path

1. **Frame it.** From the one-line request pin three things: the *subject boundary*, the
   *reader* (default: competent, but does not work in this module), and the *spine*
   (where the flow enters, where it exits). Pick a row from the Scenario router.
2. **Count the modes** — see Rule 1. Most subjects have one; decide before drafting.
3. **Collect by walking the call chain, not by reading docs.** Code first, documents last:
   documents lag behind implementations, and the gap between them is often the most
   interesting thing you will put on the page. Details in `references/collecting.md`.
4. **Draft the artifact before polishing anything.** Copy `templates/skeleton.html` and
   fill bands. **Do not redesign the layout.** The template owns geometry, color, theming,
   and responsiveness — that is what makes output stable across models and agents.
5. **Self-check**: `python <skill>/scripts/check_flow_brief.py <out.html>`, then fix in the
   order the diagnostics list.

Do not read `references/components.md` before you have a draft — consult it when you need
a component you have not used yet. Do not invent CSS classes: every visual affordance you
need already exists in the template.

## Scenario router

| Scenario | How to find the spine | How to apply the evidence ladder |
|---|---|---|
| **Shipped system or module** | Walk the call chain from the entry point | Mostly `measured` + code facts; `illustrative` only for sample payloads |
| **Upcoming feature (no code yet)** | Walk the *existing* upstream and downstream, then splice the design in between | Existing parts are `measured`/code facts; **new parts are `to build`**. The page then shows at a glance what already exists versus what must be built — exactly what a reviewer wants to know |
| **Mixed (adding to a live system)** | Spine follows the live path; new steps splice in | Both, visually separated. The `gap` color is reserved for unbuilt things |

For the upcoming-feature scenario the collection order reverses: read the design document
first, then find the existing upstream/downstream in code, then mark the seam between them.

## The five rules

Each rule exists because of a specific failure. Keep the failure in mind — it is how you
tell whether you actually applied the rule.

### Rule 1 · Separate the modes

Ask how many ways this flow can run. **Most flows have exactly one.** When that is the
case, say so in a sentence and draw one mode — do not invent a second one to make the
page look richer.

When there really is more than one, look for the split along one of these axes:

| Split axis | Typical shape |
|---|---|
| First time vs afterwards | cold start vs cache hit; index build vs query |
| Full vs incremental | bulk import vs delta sync |
| Build vs consume | index build vs query; compile vs run |
| Normal vs degraded | happy path vs fallback, retry, circuit-breaker |
| Sync vs async | answered inline vs queued for later |
| By actor | what an admin traverses vs what an end user does |

**The test: if the two ways do *different things at the same step*, they are separate
modes and each gets its own swimlane section.** If one merely *skips* steps the other
takes, it is not a mode — it is a branch, and it belongs inline as a `.band alt`.

> **Failure it prevents:** merging two genuinely different runs into one linear flow. The
> reader can then never tell which steps happen every time and which happen only once —
> and that distinction usually drives every question they ask next.

### Rule 2 · Node triad

Every step band ends with a `.dflow` strip answering exactly three questions:
**what upstream handed me / what I produced this round / who picks it up**.
All three, every band. "See above" is not an answer.

> **Failure it prevents:** the most common swimlane failure — boxes and arrows everywhere,
> but no way to see how the data actually changes shape.

### Rule 3 · Evidence ladder

Every factual claim on the page carries a provenance badge. Four rungs:

| Rung | Badge | Required backing |
|---|---|---|
| Measured | `real` pill | A run identifier, test case, or artifact path |
| Code fact | inline `code` | A `file:line` |
| Illustrative | `plan` pill | Shape is right, values invented — **must be labeled** |
| To build | `gap` pill | Not implemented yet — **must be labeled** |

> **Failure it prevents:** the single most damaging failure in a brief written for
> leadership — **drawing an intention as if it were the current state.**

The point of forced labeling is not that the reader will verify you. It is that **you
cannot fool yourself**: every cell demands a rung, and being unable to pick one is the
signal that you have not collected enough. Go back to step 3.

### Rule 4 · Three reading depths

One page serves three readers. **All three layers are mandatory.**

1. **30-second layer** — one line that sets the frame, one comparison table, and the two
   questions the reader will ask next, answered. The framing line must be *repeatable*:
   your reader will quote it to someone else. Example shape: *Checkout reserves the stock; fulfilment decides when it ships.*
2. **5-minute layer** — the swimlane itself, one band per step.
3. **On demand** — the provenance ledger: `file:line`, run identifiers, exact commands.

> **Failure it prevents:** writing for peers. Dense terminology, no framing, reader quits.

### Rule 5 · Show the gap

If you use real cases as evidence, **the last case must be one the current design does not
handle.** If you draw a path, state its known failure mode.

> **Failure it prevents:** a page that reads as marketing. The first question any competent
> reviewer asks is "so when does it not work?" — no answer collapses the credibility of
> everything above it.

In practice this section often becomes the most persuasive part of the page.

## Authoring invariants

Each carries its own repair order — apply repairs in the order given, and move to the next
only when the previous one cannot work.

- **Step granularity: one boundary crossing = one step.** A boundary crossing is: calling
  an external service, reading or writing persistent state, driving a browser or
  subprocess, crossing a process, or making an irreversible decision. Pure internal calls do
  not get their own step. *This single judgement is the main reason two different agents
  produce comparably-sized briefs from the same request.*
- **Lane count 4–6.** Below 4 a swimlane adds nothing over a list; above 6 the columns are
  unreadable. Repair: merge adjacent lanes that always act together, then split the section
  into two swimlanes, and only then reconsider the lane set.
- **Band count 8–14 per mode.** Repair: collapse consecutive same-actor steps, then move
  detail into a following table section, and only then drop a step — and if you drop one,
  say so in the section intro.
- **Every `.box` label carries at least one provenance pill** (Rule 3 is machine-checked).
- **Numbers appear only with a source.** Repair: find the source, then soften to a
  qualitative statement, then delete. Never keep a bare number.
- **Terms are explained where they first appear.** No glossary — the reader will not scroll
  back to it.
- **Comparisons go in tables, never in prose paragraphs.**
- **Counter-intuitive findings get their own `.note warn`** stating plainly which common
  assumption they overturn.
- **Evidence is a before/after pair, not a single image**, and the difference is quantified
  (a diff count, a row count, a percentage — anything better than "it changed").

## Language rules

- Lead with what the reader gets, not with how the system is built.
- One idea per sentence when the sentence carries a number or a rule.
- Name things the way the reader names them; introduce the internal term in parentheses
  once, then use it.
- Never write "simply", "just", or "obviously" — if it were obvious the page would not exist.
- Section headings state a finding, not a topic. "The cache is checked before auth" beats
  "Caching".

## Delivery

```bash
python <skill>/scripts/check_flow_brief.py <out.html>            # structural, zero deps
python <skill>/scripts/check_flow_brief.py <out.html> --visual   # + viewport/theme
```

`<skill>` is this skill's directory. The structural pass needs nothing but Python; the
`--visual` pass shells out to `check_visual.mjs` next to it.

**Exit codes are three-valued and never collapse:** `0` pass, `1` fail, `2` **unverified**
(Node or Chrome missing). `2` is not a pass. Report it as unverified.

**What counts as done:** the structural check reports 0 errors, *and* — when `--visual` is
available — the viewport check reports no horizontal overflow at any of the four widths.
A structural pass alone is a partial result; say so rather than calling it complete.

**Convergence limit.** Fix diagnostics in the order reported, re-running after each pass.
Continue while the error count reaches a new minimum. **If two consecutive rounds fail to
improve on the best count, stop and report the remaining diagnostics truthfully** instead
of churning.

**Never counterfeit a pass** with `overflow:hidden` on content, clipped elements, an
internal scroller standing in for a fixed layout, stretched heights, or shrunken type.
If a table or code block is genuinely wide it belongs in a `.tw` scroll container — that
is the sanctioned fix, and the only one.

## Known traps

Eight failures observed while producing real pages of this kind. None are hypothetical.

1. **Markdown syntax leaking into HTML.** Text authored in a markdown frame of mind lands
   in an HTML target and renders as literal `**`. After any bulk content generation, search
   the whole file for `**`.
2. **CSS class name collision.** A new component reuses a name the skeleton already binds
   and the layout breaks silently. Search the stylesheet before introducing any name.
3. **Image without `width:100%`.** When the image is narrower than its container the
   leftover strip picks up the highlight overlay and renders as a grey block.
4. **Annotation box coordinates guessed by eye.** They drift. Draw the box on the image
   with a script and confirm the hit *before* writing percentages into the page.
5. **Half a theme.** Colors defined only inside `@media (prefers-color-scheme: dark)` leave
   the un-stamped default state undefined. All three states must be present.
6. **Horizontal overflow** from wide tables and long code lines. Both belong in scroll
   containers; verify at several widths.
7. **Quoting the checker's own vocabulary trips the checker.** If your page discusses
   markdown syntax, template placeholders, or anything else the self-check greps for, the
   literal string in your prose fires the same rule it was written to catch. Write those
   as HTML entities (`&#42;&#42;`, `&#80;LACEHOLDER`) — the rendered text is identical and
   the false positive disappears. This is a real collision, not a bug in either side:
   a text-level checker cannot tell quotation from occurrence.
8. **Causal misattribution — the subtlest, and a content failure rather than a visual one.**
   Seeing "X disappeared right after action A" and attributing X to A without checking the
   link between them. This happened twice in one session and survived review both times.
   **Any claim shaped "because A happened, B changed" needs its A→B link verified
   separately** — confirming that A happened and that B changed is not enough.

## Setup and fallback

Python 3.8+ with the standard library covers the structural check. The visual check also
needs Node and a Chrome/Chromium binary; without them the checker exits `2` and you report
the visual dimension as unverified — never as passed.

**The one network dependency.** The template links Google Fonts, so a generated page
fetches three faces the first time someone opens it. That is fine on a normal laptop and
wrong in two situations: an air-gapped network, and any context where the page must not
phone out. For those, delete the three `<link>` tags in the template head — the CSS font
stacks already fall back to system faces (`PingFang SC`, `Microsoft YaHei`, `Songti SC`,
`Consolas`), so the page stays readable, just less distinctive. The visual checker will
then report the webfonts as `system-fallback`, which is expected, not a failure.

With no shell at all: walk the Known traps list by hand against the file, and state plainly
in your reply which checks you performed manually and which you could not.

## Output

Report: artifact path, scenario chosen, mode and band counts, the provenance mix (how many
cells at each rung), the check result with its exit code, and any diagnostics left unresolved.

Do not claim success for a non-zero exit. Do not claim a visual inspection you did not
perform. If Rule 5 produced nothing — if you could not find one gap worth showing — say so
explicitly, because it usually means the collection was too shallow, not that the subject
is flawless.
