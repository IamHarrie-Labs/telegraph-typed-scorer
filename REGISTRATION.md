# Registration manifest

## Status

| Reg # | Intent | Binary | Result |
|---|---|---|---|
| 2099 | GAS_PRICE | v1 `tol_loose` | **rejected** — margin 0.2197 vs champion 0.9075 |

Nothing else registered yet.

## What 2099 taught us

Two things, both of which invalidate the original plan.

**1. Telegraph states benchmark ground truth as prose, not bare values.**
`worst_self_match` came back 0.7888. The exact-match short circuit returns
exactly 1.0, so anything less proves the typed path never fired — every case
fell through to the semantic scorer. The old `MAX_ALPHA_WORDS = 4` guard only
allowed the numeric path on near-bare ground truths like `25 gwei`, and their
benchmark says things like *"the current gas price on Ethereum mainnet is
approximately 25 gwei."*

Measured effect on a prose ground truth:

| | correct answer | wrong answer | separation |
|---|---|---|---|
| v1 | 0.5564 | 0.5043 | 0.05 |
| v2 | 0.8891 | 0.1261 | **0.76** |

v2 blends the numeric reading with the semantic composite at 0.92/0.08 whenever
the ground truth is a sentence containing a number. A prose ground truth whose
answer contains *no* number falls back to semantic alone, so an answer that is
right but omits the figure is not punished to zero.

**2. Miner leaderboard scores say nothing about scorer strength.**
GAS_PRICE was picked because its miners all scored 0.000000. Its champion scorer
turned out to be excellent (0.9075). A strong scorer still emits zeros when the
miners are wrong or the ground truth is stale. The two are unrelated, and the
whole original target list was built on conflating them.

## Champion margins — the real target map

Every rejection publishes `champion_margin`, so the strength of every intent's
incumbent is public. Scanned across registrations 1980-2140:

| Intent | Champion margin | Fit |
|---|---|---|
| WEB_SEARCH | 0.3256 | prose; module ≈ baseline here |
| GAME_RESULT | 0.5605 | scores |
| TEXT_AUTHENTICITY_CHECK | 0.6154 | — |
| ACADEMIC_SEARCH | 0.6398 | — |
| RESEARCH_SYNTHESIS | 0.6599 | — |
| **ONCHAIN_TX_LOOKUP** | **0.6610** | **numeric — best fit** |
| **CRYPTO_PRICE** | **0.7333** | **numeric** |
| **STOCK_PRICE** | **0.7400** | **numeric** |
| **TVL_LOOKUP** | **0.7486** | **numeric** |
| CONTENT_MODERATION | 0.7998 | |
| LANGUAGE_TRANSLATION | 0.8000 | |
| NEWS_SEARCH | 0.8355 | |
| WEATHER_CHECK | 0.8446 | |
| TOKEN_HOLDER_COUNT | 0.8571 | numeric, but a strong incumbent |
| FACT_CHECK | 0.8667 | |
| SSL_VERIFICATION | 0.8806 | |
| CHAT_COMPLETION | 0.8991 | |
| GAS_PRICE | 0.9075 | attempted, lost |
| CURRENCY_EXCHANGE | 0.9994 | effectively unbeatable |
| CVE_LOOKUP / SENTIMENT_ANALYSIS / DEEPFAKE_DETECTION | ~1.0000 | unbeatable |

Benchmarks are small — 6 to 32 comparable cases per intent, most commonly 15.

## v2 binaries

Release: https://github.com/IamHarrie-Labs/telegraph-typed-scorer/releases/tag/v2

All three verified by anonymous fetch: HTTP 200, one redirect, bytes hash as
listed. 24,214,268 bytes each, against the 32 MB cap.

```
v2-default.wasm     TAU 0.005   prices, rates, temperatures
  0x6e7dc8ee0ca1204c26f8313e00765b7bbb94380be0b7913e4d77f0fce0c9b608

v2-tol_exact.wasm   TAU 1e-9    counts, transaction values
  0x06f3175589fa2b416f74e08c0caf6d54ae73d4863542e2d0e64775d61d1494a7

v2-tol_loose.wasm   TAU 0.05    volatile intents
  0x901cfc9b298ef784d9d5bc0257f3cadd27aefcdf42d6551878f9c66a89365050
```

Base URL for all three:
`https://github.com/IamHarrie-Labs/telegraph-typed-scorer/releases/download/v2/`

## Register these

Same binary for a *different* intent is a valid separate registration, so
`v2-default.wasm` covers four of the five.

| Priority | Intent | Binary | Champion to beat |
|---|---|---|---|
| 1 | ONCHAIN_TX_LOOKUP | `v2-tol_exact.wasm` | 0.6610 |
| 2 | CRYPTO_PRICE | `v2-default.wasm` | 0.7333 |
| 3 | STOCK_PRICE | `v2-default.wasm` | 0.7400 |
| 4 | TVL_LOOKUP | `v2-default.wasm` | 0.7486 |
| 5 | WEB_SEARCH | `v2-default.wasm` | 0.3256 |

Register several rather than one. Evaluations took over three hours on 30 Aug
and the queue is not FIFO; multiple registrations are multiple chances at
whatever queue time remains.

## Local benchmark, v2

394 cases against Telegraph's published baseline:

| Metric | Baseline | v2 |
|---|---|---|
| candidate_margin | 0.1311 | 0.9606 |
| wins | 325/394 | 394/394 |
| worst_self_match | 0.5170 | 1.0000 |
| score_stddev | 0.1535 | 0.4841 |

This corpus is ours, not Telegraph's, and 2099 proved the two differ in exactly
the way that matters. Treat it as direction, not prediction.

## Contract

- Network: Base Sepolia (chain 84532)
- Diamond: `0xac683bFa8F1C892E23e8300d14c20678C6FC0CA3`
- `registerWasm(wasmHash, wasmUrl, intent)` — gas only, no bond, no fee
- Or use the console at integrate.telegraphprotocol.com

Recompute a hash:

```bash
python -c "from Crypto.Hash import keccak;k=keccak.new(digest_bits=256);k.update(open('dist/v2-default.wasm','rb').read());print('0x'+k.hexdigest())"
```
