# The corpus drift trap: why your RAG's nDCG is probably lying to you

*A debugging story, and a 200-line tool that prevents the next one.*

---

This morning I sat down to work on a Sanskrit retrieval engine. The README claimed `nDCG@5 = 0.7891`. The bench reported `0.7620`. The gap is 0.027 — tiny in absolute terms, but the README pinned that number to a specific commit (`39f9b7c`) and said "verified." Either the README was wrong or something had silently broken. I spent the first hour assuming a code regression. I was wrong. The actual culprit is one of the most underrated bugs in modern ML evaluation, and almost every RAG pipeline I've audited has some flavour of it.

This post is the detective story. It ends with a 200-line tool that I'd put in every retrieval repo I touch from now on.

## Setup

Vāk-Kaṇaja is a small retrieval engine over thirteen classical Sanskrit and Dravidian texts — Yogasūtra, Upaniṣads, Pāṇini's grammar, Arthaśāstra, that lineage. About 6,300 text chunks. The bench is twenty-one English queries with whole-text gold labels (relevance ∈ {2, 3}) and an nDCG@5 metric. Nothing exotic.

The codebase has a pleasant rhythm: each commit on the `phase1-fractal-upgrades` branch lands one item from a research dossier, with a commit message that always includes the resulting `nDCG@5`. Authors of the previous commits had been fastidious about this — most messages literally say `score-neutral nDCG@5=X.YYYY` to flag refactors that shouldn't have moved the needle.

So when today's bench reported 0.7620 against a README that said 0.7891, my first instinct was: bisect.

## The first wrong hypothesis

The two suspect commits looked like this:

```
39f9b7c  phase1 step1.5: fractal channel disabled (winner), nDCG=0.7891
e3c2748  phase-A:  pre-Phase-8 hygiene  (10 audit items, score-neutral nDCG@5=0.7620)
8265bf1  phase-B:  verification surface (5 audit items, score-neutral nDCG@5=0.7712)
```

Look at that gap. Phase-A claims "score-neutral" but lands at 0.7620. The previous baseline was 0.7891. That's a 0.027 drop labelled as zero. Either the author miscounted, or they measured against a different state than I'm measuring against.

I started reading phase-A's diff. Twenty-one files changed. Most of it was hygiene: `print()` → `logger.info()`, `except Exception:` → typed catches, file moves, gitignore additions, requirements lock cleanup. The only retrieval-path file touched was `retrieval/kanaja_fsh.py`, with 23 line changes. I read every one. They were *all* `print` → `logger` substitutions plus one exception handler that swallowed the same exception either way (just logged it now). Truly inert.

This is when most engineers would assume the README's 0.7891 was wrong. Move on, update the README, ship.

## The second wrong hypothesis

I almost did, then noticed something. The corpus database file (`corpus/fractal_signatures.db`) had a modification time that didn't match either commit. It had been touched ~27 minutes before the phase-A commit landed. The schema, when I dumped it, had a trail of `ALTER TABLE` columns — `h2`, `asym_f`, `lacunarity` — added across multiple later commits.

In other words: the corpus DB was a moving target. The bench at any commit was reading from whatever state the DB happened to be in, not from a state pinned to that commit.

This shifted the hypothesis: maybe the regression isn't in code at all. Maybe the same code today produces a different score than the same code three weeks ago because the DB it reads has changed.

The clean test: check out `39f9b7c` in a `git worktree`, point it at today's runtime corpus DB, run the bench. If it scores 0.7891 (the README's claim), the regression is in newer code. If it scores something else, the regression is in the corpus.

```bash
git worktree add /tmp/vak39f9b7c 39f9b7c
ln -sf .../fractal_signatures.db /tmp/vak39f9b7c/corpus/fractal_signatures.db
ln -sf .../faiss_index.bin       /tmp/vak39f9b7c/corpus/faiss_index.bin
# ... and the rest of the corpus artifacts
cd /tmp/vak39f9b7c && python3 tests/sanskrit_bench.py
```

The result: **0.7206**.

## Reading the result honestly

Old code on today's corpus: 0.7206.
Today's code on today's corpus: 0.7620.
README's claim, on a corpus snapshot that no longer exists: 0.7891.

There is no recoverable regression. Old code on the new corpus is *worse*, not better — it can't take advantage of the columns added by intervening migrations, and may even be confused by their presence. The 0.7891 number was real at commit time, against an artifact state that no longer exists.

So the chain wasn't `0.7891 → regression → 0.7620`. It was three separate states being compared apples-to-oranges:

```
Commit 39f9b7c, on  corpus_state_A    →  0.7891
Commit 39f9b7c, on  corpus_state_today → 0.7206  (the actual reproducibility)
Commit HEAD, on    corpus_state_today  →  0.7620 (today's measurement)
```

The "score-neutral" annotation on phase-A wasn't false in spirit — the *code change* was indeed score-neutral. But the corpus state had drifted in the background, and the author measured against a different DB than `39f9b7c`'s author did. Neither was wrong. Both were correct. The comparison was wrong.

This is the corpus drift trap. It's invisible in `git diff`. It's invisible in the test suite. It's invisible in code review. It only manifests when someone asks "wait, where did the 0.027 go?" and tries to bisect.

## Why this matters beyond one Sanskrit engine

Every RAG pipeline I've audited has at least one of these mutating artifacts:

- **An embedding index** rebuilt when chunking strategy changes. Different chunks → different embeddings → different cosine top-k → different downstream scores. Often invisible because the chunking script is in a separate repo.
- **A BM25 cache** built once and never invalidated when tokenisation rules change.
- **A knowledge graph** that gets enriched by background jobs. Same query against the same KG returns different neighbours next month.
- **Per-document priors** — click-through rates, freshness scores, embedding-drift signals — that update on every query and silently change the ranker's behaviour.

In every case, "we ran the bench at commit X and got Y" is a true statement that *cannot be reproduced later* because Y depends on artifacts that aren't in the commit. When someone three months later cites your nDCG, they're citing a number that was real for an hour.

## The fix is small

Two pieces, totalling about 250 lines of Python.

**Piece 1 — `corpus.lock.json`.** A tool that walks every binary corpus artifact (`.db`, `.bin`, `.json`, `.pkl`), captures sha256 + size, alongside the current git commit and the verified bench score, and writes the lot to a JSON file you commit:

```json
{
  "version": 1,
  "generated_at": "2026-05-01T01:37:46Z",
  "git": {"commit": "a5cd404", "branch": "phase1-fractal-upgrades", "dirty": false},
  "artifacts": {
    "corpus/fractal_signatures.db": {"sha256": "04918ed4...", "size_bytes": 90886144},
    "corpus/faiss_index.bin":       {"sha256": "2319f9cb...", "size_bytes":  9690669},
    ...
  },
  "bench": {"nDCG@5": 0.7873}
}
```

A `--verify` mode reads the lock and exits non-zero on any sha256 drift, missing artifact, extra artifact, or git-commit drift. Future "score-neutral" claims become checkable: re-emit, diff, see exactly what changed.

**Piece 2 — bench-side feedback suppression.** The Vāk-Kaṇaja engine has a closed-loop H-update path: when retrieval seems off, it nudges the H values in the signatures DB to drift the next query toward better answers. Production-correct behaviour. But this means each bench run *mutates the corpus*, and the next bench reads a different state. The lock file would never stay green.

The fix is one env var — `KANAJA_DISABLE_FEEDBACK=1` — that short-circuits the feedback path when set. The bench harness sets it via `os.environ.setdefault` at the top of the bench file. Production deployments leave it unset.

After both pieces landed, two consecutive bench runs left the corpus byte-identical. The lock verified clean. The score was reproducible. (Bonus: the fix also surfaced two latent bugs in the feedback path — a closed-database error firing on every query and a `database is locked` race — which we patched the same afternoon.)

## What this changes about how I read RAG papers

Every retrieval claim has an implicit attached question now: *what's the sha256 of the corpus you measured against, and how do I check it?* If the answer isn't in the paper, the score is unverifiable. Not wrong, just unverifiable. That's a different category from "wrong" — but it's also a different category from "validated."

It also changes how I read commit messages. "Score-neutral" only means "I changed code that I expect doesn't move the score." It says nothing about whether the corpus the score was measured against has drifted since the previous commit. The two propositions are independent and both need to be checked.

## The simplest version you can copy

If you want to steal the pattern for your own RAG repo, the minimal diff is:

1. Write a tiny script that walks your corpus directory, hashes the binary files, dumps `corpus.lock.json`. ~80 lines.
2. Add a `--verify` mode. ~40 lines.
3. Find any code path that mutates corpus state during evaluation (feedback loops, click logging, freshness updates) and put it behind an env var that your bench sets. ~10 lines.
4. Commit `corpus.lock.json`. Run `--verify` in CI. Reject any PR that drifts the lock without a corresponding intentional re-emit.

Total cost: a couple of hours. Total benefit: every score claim in the repo becomes falsifiable, and you can finally answer "did this PR regress the bench?" without ambiguity.

The full implementation lives in [vak_engine/tools/lock_corpus_state.py](https://github.com/sparshsharma/vak_engine/blob/main/tools/lock_corpus_state.py) (Apache 2.0). Adapt freely.

---

*If you've debugged a similar drift in your own pipeline, I'd love to hear about it — `sparshsharma219@gmail.com`. I'm also taking on a small number of $5k fixed-price RAG audits where I find drift, dead code paths, and uncalibrated claims in production retrieval systems. If you're shipping retrieval and not sure your scores reproduce, [reach out].*
