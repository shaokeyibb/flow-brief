# Collecting the material

Read this when you are at Fast-path step 3 and need to know *what* to gather and *in what
order*. The ordering matters more than the thoroughness: gathering in the wrong order is
how a brief ends up describing the documentation rather than the system.

## The governing principle

**Code first, documents last.** Documentation lags behind implementation everywhere. If
you read the design document first, you will unconsciously go looking for confirmation of
it, and you will find it — that is how confirmation works. Walk the code first, form your
own picture, *then* read the documents and note where the two disagree.

The disagreement is not noise to be smoothed over. In practice it is often the single most
valuable thing you will put on the page, and it is invisible to anyone who read the
documents first.

## Scenario A — a shipped system or module

### 1. Find the entry point

Take the one that is closest to how a *person* uses the thing, in this order of preference:

1. a CLI command or subcommand
2. an HTTP route handler
3. a test case that exercises the whole path end to end
4. `main()` / the service bootstrap

A test case is often the best of these: it names the scenario, it runs, and it tells you
what the authors considered the normal path.

### 2. Walk the call chain, recording boundary crossings

Follow the call chain from the entry point. **Record one step per boundary crossing:**

| Counts as a crossing | Does not |
|---|---|
| Calling an external service or API | A pure function call |
| Reading or writing persistent state (DB, disk, cache) | Passing a value between layers |
| Driving a browser, subprocess, or device | Constructing an object |
| Crossing a process or thread boundary | A validation that cannot fail meaningfully |
| Making an irreversible decision (a verdict, a commit, a dispatch) | Logging |

This one judgement is what makes two different agents produce comparably-sized briefs from
the same request. Apply it mechanically rather than by feel.

If a stretch of code has no crossings for a long time, that is itself worth a sentence in
the section intro — "everything between X and Y is pure computation" tells the reader they
can stop worrying about that region.

### 3. For each step, capture the real contract

Do not paraphrase the inputs and outputs. Find the actual definition:

- the DTO / dataclass / struct / schema
- the function signature
- the tool or endpoint schema, if one exists

Record `file:line` for each. These become the `code fact` rung of the evidence ladder, and
they are what lets a skeptical reader check you in ten seconds.

**Prefer the schema over the prose.** When a prompt, a comment, and a schema disagree about
what a field means, the schema is what the machine obeys.

### 4. Find real artifacts — the only source of the `measured` rung

Look for, in rough order of value:

- whatever this system writes when it runs: logs, reports, event streams, job records,
  run directories, audit trails, metrics
- test fixtures captured from real executions, and golden files
- recorded payloads, screenshots, database rows, API responses saved in tests
- CI history, benchmark records, incident write-ups

The shape differs wildly by domain — a batch pipeline leaves job records, a web service
leaves request logs, a CLI leaves exit codes and stdout. **Ask what this system leaves
behind, then go read it.** If it leaves nothing you can read, that is itself a finding
worth a line on the page.

**A number without one of these behind it does not belong on the page.** If you cannot find
an artifact for a claim, either drop the claim or mark it `illustrative` and say so.

When you do find artifacts, quote them exactly — a real value with an odd shape ("attempts: 3", "0.93 confidence") is far more convincing than a rounded one, precisely because nobody
would invent it.

### 5. Only now, read the documents

Read the spec, the design doc, the README. Use them to:

- recover *intent* (code tells you what, documents tell you why)
- find the vocabulary the organisation actually uses
- **check for drift** — where the document promises something the code does not do

Any drift you find goes on the page. Mark it plainly.

## Scenario B — an upcoming feature, with no code yet

The order reverses, and the evidence ladder does the heavy lifting.

### 1. Read the design or requirement document first

There is no code to walk, so intent is all you have. Extract: what triggers it, what it
must produce, what it must not do.

### 2. Find the existing upstream and downstream in code

This is the part people skip, and skipping it is what makes new-feature diagrams useless.
The new thing does not float in space — something will call it, and it will call something.
Walk *those* with the Scenario A method. They are real, and they anchor the page.

### 3. Mark the seam

Everything you found in step 2 is `measured` or `code fact`. Everything from step 1 is
`to build`. The seam between them — the exact interfaces where new code meets old — is the
most important thing on the page, because that is where the risk lives.

Give the seam its own band or its own note. Say what already exists at that boundary
(a schema? a stub? nothing at all?) and what must be created.

### 4. Say what would have to be true

A design-stage brief earns credibility by naming its own assumptions. A short list of
"this plan assumes X, Y, Z" is worth more than another paragraph of description, and it
gives the reviewer something concrete to push back on.

## Scenario C — adding to a live system

Run Scenario A on the live path, then Scenario B on the addition, then splice: the spine
stays the existing flow, and the new steps appear inline with `gap` styling. The visual
contrast between built and unbuilt bands is the whole point — do not level it out.

## Picking a rung when it is ambiguous

| Situation | Rung |
|---|---|
| You ran it and read the output | `measured` |
| You read the code that produces it | `code fact` |
| You read a test fixture asserting it | `code fact`, and cite the test |
| You read a document claiming it, but did not verify | **not good enough** — verify, or mark `illustrative` and say the source is a document |
| The shape is right but you invented the values | `illustrative` |
| It does not exist yet | `to build` |

The rule to remember: **the badge describes how *you* know, not how confident you feel.**
Confidence is not a rung.

## Finding the gap (Rule 5)

You need at least one. Where to look, in order of yield:

1. **Error paths and terminal states** — what happens when the main flow fails? Follow one
   failure all the way to its terminal state. The place where a specific failure becomes a
   generic one is almost always a real gap.
2. **The catch-all branch** — every dispatcher has a default case. What lands there that
   should not?
3. **Recent bug fixes and their tests** — a fix tells you what broke; the neighbouring
   untested cases tell you what might still.
4. **Anything the code apologises for** — comments containing "for now", "temporary",
   "should really", "known issue".
5. **Two mechanisms that look like they overlap** — ask what falls between them. This is
   where the most interesting gaps live, because nobody owns the space between two features.

If after all five you genuinely found nothing, say so on the page and treat it as a signal
that the collection was shallow — not as proof that the system is flawless.
