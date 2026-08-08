# Stage 4 — Event extraction

Convert the findings into a flat list of atomic, dated, sourced facts. Nothing here is prose. The
point of the separation is that a model asked to write history directly from search results will
put dates in the sentences that make the sentences read well; a model writing from an already-sorted
event list cannot.

## Inputs

- Every file in `<run>/findings/`, especially the `### Dated facts` blocks.

## Task

Emit one JSON object per line into `<run>/events.jsonl`. One event per line, no wrapping array, no
trailing commas.

```json
{"date": "2021-07", "event": "Austin et al. publish D3PM, structured denoising diffusion in discrete state spaces.", "kind": "paper", "significance": "First serious attempt to move diffusion from continuous pixels to discrete tokens.", "source_url": "https://arxiv.org/abs/2107.03006", "confidence": "high"}
```

| Field | Required | Notes |
|---|---|---|
| `date` | yes | `2021`, `2021-07`, `2021-07-15`, `2021-Q3`, or an approximate `~2021`, `early 2021`, `mid-2021`, `late 2021` |
| `event` | yes | One sentence, one fact, past tense, names the actor |
| `source_url` | yes in practice | The URL supporting it. Use `sources` with a list when several do |
| `kind` | no | `paper`, `method`, `release`, `benchmark`, `tooling`, `org`, `milestone` |
| `significance` | no | What this *changed* relative to what came before — the improvement, not a restatement |
| `confidence` | no | `high`, `medium`, `low`. Low when only one weak source supports it |

Aim for 12–30 events. Under about 8, or spanning fewer than three years, the timeline builder will
reject the run as too sparse to be a history — and it will be right.

Include the negative space. Approaches that were tried and abandoned, results that failed to
replicate, and predictions that did not land explain why the field moved more clearly than the
successes do. They are events.

## Then run the builder

```bash
python research/scripts/build_timeline.py research/runs/<run-id>
```

It validates every record, merges the same event reported by two perspectives, sorts, and writes
`timeline.md` and `timeline.json`. Exit code `2` means it needs a decision from you:

| Verdict | What to do |
|---|---|
| `malformed_records` / `unparseable_dates` | Fix or delete the named lines and re-run |
| `missing_sources` | Add the URL, or `--drop-unsourced` if the event is not worth keeping |
| `sparse_timeline` | Go back to stage 3 and search explicitly for prior art. Only `--allow-sparse` when the topic genuinely has no deeper history |

Read the `merged:` lines it prints. A wrong merge silently loses an event; if two distinct things
were collapsed, reword one of them so they stop looking alike, and re-run.

## Rules

- **No undated events.** An undated fact cannot anchor a narrative. If a source gives no date, the
  fact belongs in the findings, not the timeline.
- **Atomic.** "X published Y, which led Z to build W" is two events, possibly three.
- **`significance` is the whole point of the run.** It should say what became possible that was not
  possible before. If you cannot say that, the event may not be a major improvement.
- Do not add events from memory. Every line traces to a findings file.
