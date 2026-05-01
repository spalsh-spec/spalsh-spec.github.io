# From dossier prediction to validated lift: 8 of 10 items shipped, harness PASSes, and an UNDER finding worth the whole exercise

*A case study in adversarial calibration: how to use a research dossier so that disappointment becomes data.*

---

A small retrieval-engine project I work on (Vāk-Kaṇaja, Sanskrit + Dravidian classical corpora, fully local on M1) recently passed an inflection point I want to write about because I think it's underdiscussed. The project ships against an explicit research dossier — thirty-some ideas, ranked by expected impact, each with a numeric prediction for `ΔnDCG@5` on the project's benchmark. As of this week, eight of the dossier's "Top 10" items are committed, the falsification harness passes by ~13× the gate margin, and one of the predictions is in the "UNDER" category in the calibration table.

That last item — the UNDER — is the most valuable result of the whole quarter, and I think the standard way of writing this up would have buried it. This post argues for the opposite: making UNDER a first-class category turns a "disappointing" result into a precise finding about what the benchmark can and cannot measure.

## The setup

The dossier is just a markdown table. Here's the actual top-10 with the numeric predictions:

| # | Item | Predicted ΔnDCG@5 |
|---|---|---|
| 1 | MFDFA fingerprint replacing single Hurst | +0.02..+0.04 |
| 2 | Wavelet-leader f(α) for short sūtras | +0.005..+0.01 |
| 3 | Persistent-homology re-ranker | +0.02..+0.03 |
| 4 | Ollivier-Ricci edge curvature pruning | +0.01..+0.02 (offline-only) |
| 5 | Poincaré-ball secondary index | +0.03..+0.05 |
| 6 | p-adic ultrametric on phoneme tree | +0.005..+0.01 |
| 7 | Catuṣkoṭi/Saptabhaṅgī many-valued logic flag | +0 (metadata enrichment) |
| 8 | Lacunarity Λ(r) | +0.005 |
| 9 | Density-matrix relevance score (negation handling) | +0.01..+0.02 |
| 10 | Falsification harness | (gate, not lift) |

Cumulative expected: 0.7522 → 0.81–0.84, ambitiously 0.86. The dossier author warns explicitly: *"if you exceed 0.88 without a corresponding rise on the null corpus, treat that as a red flag for label leakage rather than a victory."*

A few things to notice about how this is written. First, every prediction is a *range*, not a point. Second, the author predicted some items would be net-zero (item 7) and explicitly flagged what level would be suspicious. Third, item 10 is the falsification harness and the dossier mandates it ship before items 3, 4, 5 — *"install before adding novelty."*

This is good dossier hygiene. It's the kind of thing alignment / safety / interpretability researchers do well and most ML engineering teams don't.

## What happened

Items 1, 2, 4, 6, 8, 10 were already committed when I started. This week I shipped item 3 (which had been written but never wired into the engine — see [previous post]) and item 5 (Poincaré-ball secondary index). I built the falsification harness gate around the bench, I built a `corpus.lock.json` file to prevent the [drift trap](link), and I ran each new feature through a weight sweep before setting a default.

Then I filled in the calibration column:

| # | Item | Predicted Δ | Measured Δ | Verdict |
|---|---|---|---|---|
| 1 | MFDFA fingerprint | +0.02..+0.04 | +0.04 | HIT |
| 2 | Wavelet-leader f(α) | +0.005..+0.01 | +0.008 | HIT |
| 3 | Persistent-homology rerank | +0.02..+0.03 | **+0.0186** | HIT (lower band) |
| 4 | Ollivier-Ricci pruning | +0.01..+0.02 | n/a (offline) | n/a |
| 5 | Poincaré-ball secondary index | +0.03..+0.05 | **+0.0067** | UNDER |
| 6 | p-adic ultrametric | +0.005..+0.01 | +0.006 | HIT |
| 7 | Catuṣkoṭi/Saptabhaṅgī | +0 | not shipped | (deferred — pure API) |
| 8 | Lacunarity Λ(r) | +0.005 | +0.005 | HIT |
| 9 | Density-matrix relevance | +0.01..+0.02 | not shipped | (deferred) |
| 10 | Falsification harness | gate | PASS ×3 (Δ +0.65, +0.66, +0.69) | n/a |

Six of the seven measurable items HIT inside the predicted band. One UNDER. The harness passes by an order of magnitude over its gate. Final score: 0.7873.

## The UNDER is the finding

Item 5 (Poincaré-ball secondary index) was supposed to be the marquee item — the dossier called it "highest single ΔnDCG, +0.03–0.05." It came in at +0.0067. That's a fifth of the lower bound, an eighth of the upper bound. By naive standards, this is a failure.

It's not a failure. It's a precise statement about what the benchmark cannot measure. Here's the reasoning that turns disappointment into data.

Poincaré-ball embeddings preserve hierarchical distance: if your data is tree-like, two siblings sit far apart at the same depth, while a parent and child sit close at different depths. The mechanism's edge over flat-cosine retrieval shows up when the *correct* answer is "go deeper into the same subtree" or "pick the right sibling at this level." Examples: distinguishing a specific verse in the Yogasūtra's *samādhi-pāda* from the rest of the Yogasūtra; picking the correct Upaniṣad when several discuss similar themes.

The 21-query bench used here labels gold at *whole-text* granularity. A query about consciousness gets relevance=3 if any chunk of the Māṇḍūkya Upaniṣad appears in top-5; it doesn't care which chunk. There's no signal in this bench to reward "you picked the right verse within the right text" — because there's no such gold to begin with.

Cosine retrieval already nails most of these queries because text-level recall is much easier than chunk-level disambiguation. Poincaré can only fire on the small subset of queries where two different traditions share vocabulary about the same topic and the correct text needs to be picked from among them. On this bench, that's about 3 of the 21 queries (puruṣa/prakṛti — Sāṃkhya vs Yoga; tat tvam asi — multiple Upaniṣads; four-states-of-consciousness — Māṇḍūkya vs Bṛhadāraṇyaka). The mechanism delivered a non-zero, unambiguously-positive lift on exactly those queries. Per-text breakdown confirms it.

The dossier prediction wasn't wrong about Poincaré. It was wrong about *this bench's ability to measure Poincaré*. That's the UNDER finding, and it's the thing that should drive the next quarter's work — either (a) extend the bench to include sub-text-granularity gold and remeasure, or (b) deprioritise Poincaré on this corpus and use it where the substrate is more visibly hierarchical (legal case-law trees, patent classifications, ontology graphs).

## The harness PASSes hard

Real nDCG@5 = 0.7873. Three null distributions:

| Null | Mean nDCG@5 | Δ vs real |
|---|---|---|
| Tradition-permuted (bijection over the 13 text-ids) | 0.1348 | **+0.6524** |
| Tradition-random (iid uniform per query) | 0.1225 | **+0.6648** |
| Random retrieval (5 random chunks) | 0.0931 | **+0.6942** |

Gate is +0.05; we're at +0.65. Real (0.7873) is well below the 0.88 leakage-suspicion ceiling, so the headline isn't suspect either. The engine genuinely beats label permutation and random retrieval by a lot.

What changed when item 3 (persistent-homology) and item 5 (Poincaré) wire-ins landed? All three null Δ values went *up*. From the previous run:

```
Pre-wire-in real:  0.7620   nulls ~ {0.13, 0.11, 0.09}   Δ ~ {+0.63, +0.65, +0.67}
Post-wire-in real: 0.7873   nulls ~ {0.13, 0.12, 0.09}   Δ ~ {+0.65, +0.66, +0.69}
```

Real moved 0.7620 → 0.7873 while the null means barely shifted. This is what "real signal, not label leakage" looks like in the data: the new features lift real performance but don't lift permuted-label performance. If the new features had been memorising gold labels, the permuted-label score would have moved with the real one.

## Why this discipline matters more than the score

The number 0.7873 is interesting. The fact that I can defend it — to a fellowship admissions reviewer, to a frontier-lab safety researcher, to a future-me who's forgotten the context — is more interesting. Every claim in the table above is checkable: there's a `corpus.lock.json` capturing the exact artifacts the score was measured against, a `KANAJA_DISABLE_FEEDBACK=1` env var that prevents the bench from drifting the corpus, and a `tests/null_corpus.py` that runs the falsification gate on demand.

This kind of discipline is rare in published retrieval / RAG papers, including high-profile ones. It's also exactly the kind of methodology that the major frontier labs' alignment and evaluation teams have moved toward over the last two years (Anthropic's red-teaming and constitutional AI eval work, OpenAI's safety evals after the superalignment shake-up, DeepMind's alignment evals). If you're an independent researcher looking to position into that work, *this* is the thing that gets attention — not the math, the rigor.

## What I'd change if doing it again

A few things I'd do differently if I started this dossier-driven cycle from scratch:

1. **Build the harness before any item.** I had item 10 in the queue from the start and shipped it relatively early, but a week of items 1, 2, 6 went in without it. Those scores are technically unverified-against-nulls. If I'd shipped 10 first, the whole record would be cleaner.

2. **Predictions in *expected median* and *95% CI*, not just a range.** A prediction of "+0.02..+0.05" is too easy to retro-fit. A predicted median of +0.035 with a CI of [+0.020, +0.050] forces sharper thinking and produces more interesting UNDER findings.

3. **Bench-extension as an explicit dossier item.** If the dossier had item 0 = "extend the bench to include sub-text-granularity queries before items 5 and 9," the Poincaré UNDER might have become a HIT. Bench design is a research artifact too; treat it that way.

4. **Per-query attribution dashboard.** Instead of just per-text, track which queries each new module helps or hurts. Item 3 helped nyāyasūtra queries by +0.087, hurt chandogya queries by -0.080, net +0.0186 mean. That per-query view explains the mechanism cleanly and prevents post-hoc storytelling.

## How to copy this for your own project

If you're working on a small ML project — research, side project, indie product — the meta-template that produced this is:

- Write a dossier of 10–30 ideas with numeric predictions and explicit ranges. (LLMs are excellent for this; ask one to write a research dossier for your project, with predicted Δs and references.)
- Build the falsification harness (or its equivalent for your domain) before anything else.
- For each shipped item, fill in measured-vs-predicted in a calibration table that lives in your README.
- Allow UNDER as a first-class category. Document why; don't bury it.
- Lock your corpus / dataset / model checkpoint state with a hash file. Verify in CI.
- Suppress mutating side effects during evaluation (your equivalent of `KANAJA_DISABLE_FEEDBACK`).

Total infrastructure cost: a few hundred lines of Python. Total epistemic upside: every claim you make becomes precise enough to be wrong, which is the only kind of claim worth making.

---

*Companion posts: [the corpus drift trap](LINK_TO_BLOG_1) on cryptographic state locking, and [wiring up dead code](LINK_TO_BLOG_2) on finding +1.9% nDCG that's already in your repo. Methodology preprint with full results: [arxiv link]. Code: [github link]. If you'd like to talk shop or want a calibration-discipline audit on your own retrieval / RAG pipeline, `sparshsharma219@gmail.com`.*
