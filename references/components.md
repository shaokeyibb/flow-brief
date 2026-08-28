# Component reference

Look here when you need a component you have not used yet. Every class below already
exists in `templates/skeleton.html` — **do not invent new ones**, and do not restyle these.
The template owning all geometry is what makes output consistent across models.

## Pills — the provenance and cost badges

`.pill` alone has no color; it must be paired with a variant.

```html
<span class="pill real">measured</span>      <!-- from a real run: cite run id / case -->
<span class="pill plan">illustrative</span>  <!-- shape real, values invented -->
<span class="pill gap">not built</span>      <!-- reserved for unbuilt things -->
<span class="pill ext">calls out</span>      <!-- crosses a boundary -->
<span class="pill pure">stays local</span>   <!-- pure, in-process -->
<span class="pill mute">step 2 of 3</span>        <!-- neutral counter -->
```

`gap` is reserved. Never use the red family for anything that actually works — a reader
who learns that red means "unbuilt" in one place will read it that way everywhere.

## Swimlane skeleton

```html
<div class="flow">
  <!-- one <span> per lane: draws the dashed guide line down the page -->
  <div class="lanes"><span></span><span></span><span></span><span></span><span></span></div>

  <!-- sticky header; lane count must match .lanes exactly -->
  <div class="lanehd">
    <div><b>Lane name</b>what it owns</div>
    <!-- ...one per lane -->
  </div>

  <!-- bands go here -->
</div>
```

The rail carries the arrow. `grid-column:M/N` places it across lanes M..N-1.

```html
<div class="band">
  <div class="rail"><div class="hop ext" style="grid-column:2/4"></div></div>
  <div class="body extb">…</div>
</div>
```

| Rail variant | Meaning |
|---|---|
| `hop` | deterministic step (teal) |
| `hop ext` | leaves the process (amber) — pair with `body extb` |
| `hop gap` | not built (red) — pair with `body gapb` |
| `hop rev` | reverse direction: dot on the right, arrowhead on the left |

An alternate or offline branch uses `band alt` plus a divider:

```html
<div class="band alt">
  <div class="rail"><div class="hop rev" style="grid-column:2/6"></div></div>
  <div class="body">
    <div class="altbar">offline branch · replaces A2</div>
    …
  </div>
</div>
```

## Inside a band — the required order

`step → plain → [cmd] → io → [note] → dflow`

`.dflow` is always last and is never optional.

```html
<div class="step">
  <span class="n">A4</span>
  <span class="t">What happens here, in the reader's words</span>
  <span class="badges"><span class="pill ext">calls out</span></span>
</div>
<p class="plain">Two or three sentences. <b>Bold the non-obvious clause.</b></p>
```

`.badges` is pushed right automatically; it can hold several pills.

## In / out comparison

```html
<div class="io">
  <div class="box">
    <div class="lbl">goes in <span class="pill plan">illustrative</span></div>
    <div class="what">Plain-words framing of the payload:</div>
<pre><span class="k">field_one</span>   what it carries
<span class="k">field_two</span>   what it carries
             <span class="c">// why this one matters</span></pre>
    <div class="cap">contract: path/to/file.py:120</div>
  </div>
  <div class="arrow">→</div>
  <div class="box">
    <div class="lbl">comes out <span class="pill real">measured</span></div>
    <div class="what">A <b>real</b> value, quoted exactly:</div>
<pre>{ "kind": <span class="s">"example"</span>, <span class="k">"attempts"</span>: 3 }</pre>
    <div class="cap">run-0042 · example-case</div>
  </div>
</div>
```

Highlight spans inside `.box pre`: `.k` key, `.s` string, `.c` comment.

**Every `.lbl` must carry a provenance pill** — this is machine-checked.

## Data-flow strip (Rule 2, mandatory)

```html
<div class="dflow">
  <div><i>upstream gave me</i>← what arrived, and from which step</div>
  <div><i>produced this round</i>the artifact this step creates</div>
  <div><i>picked up by</i>→ which step consumes it, and for what</div>
</div>
```

Exactly three `<i>` cells. The checker counts them.

## Notes

```html
<div class="note">        <span class="l">neutral aside</span>       <p>…</p></div>
<div class="note good">   <span class="l">the point of this</span>   <p>…</p></div>
<div class="note warn">   <span class="l">this overturns X</span>    <p>…</p></div>
```

Use `note warn` for counter-intuitive findings, and say plainly in the label which common
assumption the finding overturns. That label is what makes the page feel honest.

## Commands

```html
<div class="cmd">
  <span class="l">entry point</span>
<pre><span class="p">$</span> mytool <span class="f">--flag</span> value \
    subcommand <span class="c"># what this does</span></pre>
  <div class="n">A sentence about what the command means for the reader.</div>
</div>
```

`cmd todo` (purple) marks a command that does not exist yet.
Spans: `.p` prompt, `.f` flag, `.c` comment.

## Tables

```html
<div class="tw"><table>
  <thead><tr><th>Column</th><th>Column</th></tr></thead>
  <tbody>
    <tr><td class="m">mono cell</td><td>prose cell</td></tr>
  </tbody>
</table></div>
```

Always wrap in `.tw` — the checker enforces it. `td.m` renders a cell in the mono face;
use it for identifiers, codes, and step numbers.

## Screenshots and annotation boxes

```html
<div class="shot">
  <img src="data:image/jpeg;base64,…" alt="what is visible">
  <span class="mark" style="left:80.6%;top:11.5%;width:2.8%;height:5.5%"></span>
  <span class="mtag" style="left:62%;top:5%">the target</span>
</div>
```

`.mark` dims everything outside itself with a huge box-shadow, so the box reads as a
spotlight. Coordinates are percentages of the container.

**Verify coordinates before writing them.** Draw the rectangle onto the image with a
throwaway script, look at the result, and only then copy the percentages into the page.
Coordinates estimated by eye drift, and a spotlight on the wrong element is worse than no
spotlight at all.

Keep images at a sensible size before embedding — roughly 700–900 px wide at JPEG quality
70 is plenty for a page like this, and keeps the file small enough to open instantly.

## Legend and header

```html
<header class="top">
  <div class="wrap">
    <p class="kicker">SUBJECT · SCOPE</p>
    <h1>A finding, not a topic</h1>
    <p class="lede">One paragraph a non-specialist can finish. <b>Bold the clause that matters.</b></p>
  </div>
</header>
```

```html
<div class="keys">
  <div class="key"><div class="h">section label</div><div class="b">content</div></div>
</div>
```

## Traps in these components

- **`.box` needs `min-width:0`** (already in the template) or the inner `<pre>` will not
  scroll and will instead blow out the grid.
- **`<pre>` must start at column 0.** Its content is whitespace-preserved, so any leading
  indentation you add for tidiness shows up on the page.
- **`.pill` on its own has no color.** Always add a variant.
- **`table` needs its `min-width`** (already in the template) — that is what arms the `.tw`
  scroll container. Removing it does not "fix" a wide table; it just moves the overflow to
  the page.
- **Do not add new class names.** If you find yourself wanting one, you are probably about
  to restyle something the template already solves. Check this file first.
