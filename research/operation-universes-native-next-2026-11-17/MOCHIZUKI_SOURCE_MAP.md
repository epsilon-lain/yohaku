# Mochizuki source map for operation universes

Prepared 2026-11-17. Primary sources only. This is a small inspiration packet for a separate research program, not a review of IUT, a claim about the acceptance of ABC, or evidence that IUT proves an algorithmic speedup.

## Official source catalog and pagination

Author for all entries: **Shinichi Mochizuki**.

Official author/RIMS catalog: <https://www.kurims.kyoto-u.ac.jp/~motizuki/papers-english.html>, section “Inter-universal Teichmuller Theory”, entries [1]–[5]. Verified links on 2026-11-17.

| ID | Title | Exact official PDF URL | Priority |
|---|---|---|---|
| PANO | A Panoramic Overview of Inter-universal Teichmüller Theory | https://www.kurims.kyoto-u.ac.jp/~motizuki/Panoramic%20Overview%20of%20Inter-universal%20Teichmuller%20Theory.pdf | Essential excerpts below |
| IUT1 | Inter-universal Teichmüller Theory I: Construction of Hodge Theaters | https://www.kurims.kyoto-u.ac.jp/~motizuki/Inter-universal%20Teichmuller%20Theory%20I.pdf | Essential excerpts below |
| IUT2 | Inter-universal Teichmüller Theory II: Hodge-Arakelov-theoretic Evaluation | https://www.kurims.kyoto-u.ac.jp/~motizuki/Inter-universal%20Teichmuller%20Theory%20II.pdf | On demand only |
| IUT3 | Inter-universal Teichmüller Theory III: Canonical Splittings of the Log-theta-lattice | https://www.kurims.kyoto-u.ac.jp/~motizuki/Inter-universal%20Teichmuller%20Theory%20III.pdf | Catalog only; no reading assigned |
| IUT4 | Inter-universal Teichmüller Theory IV: Log-volume Computations and Set-theoretic Foundations | https://www.kurims.kyoto-u.ac.jp/~motizuki/Inter-universal%20Teichmuller%20Theory%20IV.pdf | Catalog only; no reading assigned |

**Pagination is for these author-hosted PDFs, not the journal layouts.** PANO has 45 PDF pages; IUT1 has 186, with “May 2020” on its first page. PANO's catalog revision is dated 2013-08-20. In both PDFs the internal printed page number equals the one-based PDF page number. Zero-based page index = printed page minus 1. These counts and selected page text were checked directly from the downloaded PDF bytes in memory. The alternative RIMS1774 PDF has an institutional cover and must not silently reuse these page indices.

## Essential packet: eleven pages, in this order

| Order | Source | Internal printed pages | PDF pages (one-based) | PDF indices (zero-based) | Grounded paraphrase / reading target |
|---|---|---|---|---|---|
| 1 | PANO | 11 | 11 | 10 | The proposed assignment uses distinct ring/scheme-theoretic copies. Dismantling structure entails measuring distortion; invariant structures are called cores. |
| 2 | PANO | 28–29 | 28–29 | 27–28 | Hodge theaters separate additive and multiplicative finite-field symmetries, with different strengths and indeterminacies. The logarithmic link is not a ring homomorphism. |
| 3 | PANO | 38–40, §4 opening and Theorem 4.1 | 38–40 | 37–39 | Non-ring links do not automatically induce Galois-group maps. Abstract groups replace field-action labels; reconstruction describes structures across the link. Theorem 4.1 concerns a multiradial description, not runtime. The Gaussian accuracy comparison is an analogy. |
| 4 | IUT1 | 1, Abstract | 1 | 0 | Isomorphism of theaters does not make their Θ-link compatible with ring structure. The author describes relating those structures with indeterminacies using anabelian geometry. |
| 5 | IUT1 | 12–15, end of §I1 and Theorem A | 12–15 | 11–14 | The initial Θ-link is simplified. The Frobenius picture retains ordered-link information; its étale picture has a common core and permutation symmetry. Reconstruction is described through this setting. Theorem A specifies the constructed objects and links. |

Do not inject complete PDFs into model context. Supply these excerpt ranges, source identifiers, and local page metadata; expand only to answer a concrete definition or proof-dependency question.

## Optional two-page follow-up

IUT2, internal printed pp. 3–4, PDF pages 3–4, zero-based indices 2–3: “coric” algorithms depend on the common core; “uniradial” descriptions use their own spoke; “multiradial” descriptions use coric objects intelligible at other spokes. The latter may require indeterminacy. This is a useful vocabulary check, not a computational complexity bound. No IUT3/IUT4 pages are assigned at this stage.

## Translation into the independent operation-universes project

These are **project questions**, not conclusions of the cited papers:

1. For an addition-only or multiplication-only capability model, state the carrier, constants, permitted operations, encoding, and desired output before asking what can be reconstructed. IUT's additive/multiplicative symmetry discussion is not an addition-only/multiplication-only machine model.
2. For each proposed transport, distinguish exact preservation of the chosen algebraic operations from a representation useful for a particular query. An isomorphism's existence does not establish that the particular link used preserves those operations.
3. For a composition chain, record each map's domain, codomain, recoverable invariants, ambiguity, and compatibility with the next map. Do not identify separate copies or labels merely because they look alike.
4. For an advantage claim, charge encoding, conversion, preprocessing, intermediate size, precision, ambiguity resolution, decoding, and verification. Compare equal input/output tasks under an explicit cost model. Mathematical reconstruction algorithms in these excerpts supply no such ledger or speedup theorem.

Evidence gate: any claimed bridge from these passages to a concrete arithmetic algorithm requires a separately stated construction and proof. Do not label an unproved heuristic as an IUT consequence, and do not treat arithmetic degree/log-volume estimates as operation counts.
