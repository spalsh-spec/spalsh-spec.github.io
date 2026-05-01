# Wiring up dead code: how I found +1.9% nDCG sitting unused in my own repo

*Most production RAG pipelines have features that were "shipped" months ago and are silently doing nothing. Here's how to find yours.*

---

A few weeks ago, a previous version of me — same engineer, different mood — committed this with a clean message:

```
phase1 step3: persistent-homology re-ranker (dossier §2.2 #3)
```

The commit added a 314-line module, `retrieval/topo_rerank.py`, with rigorous docstring, ripser/persim dependencies installed cleanly, and a small unit-test suite that passed. The module's design had been sketched in the research dossier, validated in isolation, and merged. By every visible signal — green tests, passing lint, sensible commit message — the feature was shipped.

Today I noticed something. The bench score hadn't moved on that commit. Not by 0.001. The dossier had predicted +0.02–0.03 nDCG@5 from this re-ranker; the reality was zero.

Spoiler: the function existed but was never called from anything except its own tests. Wiring it in took 17 lines. The score went from 0.7686 to 0.7873. **One commit, +0.0186 nDCG, ~3% relative lift, recovered with no algorithmic change at all.**

This pattern is common enough that I'd bet you have a version of it in your own RAG pipeline right now. Here's how to find it.

## The two-minute audit

Pick any feature in your retrieval system that you think is "shipped." Run this:

```bash
grep -rn "from .* import <feature_name>\|import .*<feature_name>" \
    --include="*.py" .
```

Now subtract any matches that come from `tests/` or from the module itself. What's left is the set of production-code call sites for that feature. If that set is empty, you're not using it.

For me, the result was:

```
$ grep -rn "topo_rerank\|from retrieval.topo" --include="*.py" .
./retrieval/topo_rerank.py:1:"""..."""
./retrieval/topo_rerank.py:180:def topo_rerank(...
./tests/unit/test_topo_rerank.py: ... (the only callers)
```

Three matches in the source file (defining itself), one in the test file. **Zero in the engine entry point.** That's a feature that exists exclusively for the satisfaction of its tests.

## How this happens

It's not negligence. It's a specific dynamic that produces this outcome over and over:

1. **Research and integration are scoped separately.** The dossier said "ship the formalism + tests first, integrate after." That's a sensible engineering norm. But the integration ticket gets deprioritised by the next exciting research item, and the original integration intent fades from memory.
2. **The commit message lies cleanly.** "Persistent-homology re-ranker" sounds done. The diff shows the function. The tests pass. Reviewers approve. Nothing in the surface signal indicates the function is dead.
3. **Score regression tests don't catch dead code.** If you ship a feature wired to weight=0 by default, the bench score doesn't move. If you ship a feature *not wired in at all*, the bench score also doesn't move. From the bench's perspective, these are indistinguishable.

This last one is critical. The most common way teams catch missing integration is "the score got worse after the wire-in PR" — but that only fires once you actually attempt the wire-in. Dead code that no one tries to wire in stays dead forever.

## The systematic fix

For any retrieval pipeline of nontrivial size, I now do this once a quarter and once whenever I'm new to a codebase:

**Step 1 — Inventory the rerankers.** List every function whose docstring or name implies it modifies the retrieval ranking. Don't trust the directory structure or the commit messages. Read.

**Step 2 — Trace each one to a call site outside its own tests.** Use the grep above. Anything without a production call site is either dead code or scaffolding awaiting integration.

**Step 3 — Distinguish the two cases.** If it's scaffolding awaiting integration, wire it in (with a default weight of 0 if you want zero behaviour change), then sweep its weight to find the peak. If it's dead code with no plausible value, delete it — keeping it costs you cognitive load on every future grep.

**Step 4 — For each newly wired feature, run the falsification harness.** Make sure it's not adding label leakage. (If you don't have a falsification harness, that's a separate post.)

The whole audit took me about 90 minutes per pipeline.

## The wire-in itself

In case it helps, here's exactly what the integration looked like for the persistent-homology reranker. The pre-existing function took:

```python
topo_rerank(
    query_embedding: np.ndarray,            # (D,) query vector
    candidate_embeddings: np.ndarray,       # (K, D) top-K from prior stage
    candidate_ids: Iterable,
    *,
    score_mode: str = "image_l2",
    top_k: Optional[int] = None,
) -> list[tuple[object, float, dict]]
```

Its own docstring warned: *"Scores are unitless. To fuse with the existing ranker, normalise (z-score or rank-transform) both scores then combine with a weight."* So the wrapper rank-transforms then adds:

```python
def topo_persistence_rerank(
    reranked,
    query_embedding,
    embedding_lookup,
    topo_weight=None,
    top_k=50,
):
    if topo_weight is None:
        topo_weight = CHANNEL_WEIGHTS["topo"]   # read at CALL time, not def time
    if topo_weight == 0.0 or len(reranked) < 3:
        return reranked

    # Pull (K, D) embeddings for the top-K candidates from the engine's FAISS
    head = reranked[:top_k]
    embs, valid_ids = [], []
    for cid, _, _ in head:
        emb = embedding_lookup(cid)
        if emb is not None:
            embs.append(emb); valid_ids.append(cid)
    if len(embs) < 3:
        return reranked

    topo_results = topo_rerank(query_embedding, np.array(embs), valid_ids)

    # Rank-transform to [0, 1] so weight competes on the same scale as RRF.
    raw = {cid: float(s) for cid, s, _ in topo_results}
    sorted_cids = sorted(raw, key=lambda c: raw[c])
    n = max(len(sorted_cids) - 1, 1)
    rank_norm = {cid: i / n for i, cid in enumerate(sorted_cids)}

    out = []
    for cid, score, stats in head:
        boost = topo_weight * rank_norm.get(cid, 0.5)
        out.append((cid, score + boost, {**stats, "topo_rank": rank_norm.get(cid)}))
    out.sort(key=lambda t: t[1], reverse=True)
    return out + reranked[top_k:]
```

Plus the one-line call site in the engine:

```python
reranked = topo_persistence_rerank(reranked, enc["full_emb"], _embed_lookup)
```

Total: 50ish lines of wrapper, 1 call site, 1 line for the channel weight default. Zero algorithmic novelty. Module already existed. Tests already passed.

## The two traps inside the wire-in

If you do this exercise, watch for these:

**Trap 1: closure-capture on the weight default.** Tempting to write:

```python
def topo_persistence_rerank(reranked, ..., topo_weight=CHANNEL_WEIGHTS["topo"]): ...
```

This binds `topo_weight` to whatever `CHANNEL_WEIGHTS["topo"]` was at *function-definition time*. When you later monkey-patch the global to sweep weights, the default doesn't update. Your sweep silently runs at the original weight every time. (I caught this on the first sweep — it produced six identical rows.) Use `topo_weight=None` and read the global on the first line of the function body.

**Trap 2: scale mismatch.** Re-ranker scores from different mechanisms have different natural scales. RRF scores in my pipeline live in roughly [0.001, 0.02] — gaps between consecutive ranks are around 0.001. If you blindly add `weight × raw_score` where `raw_score` happens to be in [0, 1], even a tiny weight (0.05) produces a perturbation 30× larger than the RRF gap, completely overwriting the existing ranking. The result is unimodal: a sharp peak at one specific small weight, with a knee just past it where the score crashes. My sweep showed:

```
w        nDCG@5    Δ
0.0000   0.7686    baseline
0.0005   0.7686    +0.0000  (perturbation below RRF gap)
0.0010   0.7873    +0.0186  ← peak
0.0020   0.7853    +0.0166
0.0050   0.7236    -0.0450  (over the knee)
0.0100   0.5712    -0.1974  (chaos)
```

Always rank-transform or z-score the new feature before combining, and always sweep on a logarithmic ladder that includes weights smaller than your RRF gap.

## The meta-lesson

The biggest available wins in a retrieval pipeline are usually not new algorithms. They are dormant features waiting for someone to wire them in correctly. This is true partly because of the integration-vs-research split above, partly because the kind of person who writes a clever rerank module is often not the kind of person who patches the engine to call it, and partly because the bench tells you nothing when integration is missing.

I'm now constitutionally suspicious of any retrieval repo where the rerankers are in a `retrieval/` directory and I can't immediately see them being called from the engine entry point. If they're not called, they're either decoration or pending work. Either way, treat them as a TODO.

---

*This was the second of three blog posts on what I learnt rebuilding the verification surface of a small Sanskrit retrieval engine. The first was on [corpus drift](LINK_TO_BLOG_1). The third (forthcoming) is on calibrating predicted-vs-measured Δ on a research dossier so failures become findings, not embarrassments.*

*If you'd like a fixed-price audit of your retrieval pipeline — dead code, drift, uncalibrated claims, and a written report — I'm taking 2 per month at $5k. Email `sparshsharma219@gmail.com`.*
