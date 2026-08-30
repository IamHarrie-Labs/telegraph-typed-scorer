# Telegraph Typed Scorer

A WASM scoring module for [Telegraph Protocol](https://telegraphprotocol.com/)
that compares numeric answers **as numbers**.

Telegraph's scoring modules decide which miners get paid. The reference module
scores an answer by embedding similarity plus word overlap plus a length bonus.
That works on prose and fails on numbers: the word-overlap term splits text on
non-alphanumerics, so `111240.55 USD` and `111238.02` share no token at all. A
price two dollars out is, to that scorer, as wrong as a poem.

This module adds one thing. If the ground truth is a number, compare the values
and score by relative error. If it isn't, fall through to the inherited
semantic scorer, untouched.

That fallback is the design. Telegraph promotes a candidate only if it beats the
incumbent on a hidden benchmark. By leaving prose scoring byte-identical, this
module can only tie or beat the baseline there, while the typed path is pure
upside on the intents the baseline scores at its floor.

## Results

394 cases, head to head against Telegraph's published baseline, both built with
real MiniLM-L6-v2 weights and driven through the same calling convention the
node uses.

| Metric | Baseline | Typed | Gate |
|---|---|---|---|
| `candidate_margin` | 0.1311 | **0.9587** | ≥ baseline |
| `wins` | 325/394 | **394/394** | ≥ baseline |
| `worst_self_match` | 0.5170 | **1.0000** | ≥ 0.75 |
| `score_stddev` | 0.1535 | **0.4834** | above floor |

Per intent:

| Intent | Baseline margin | wins | Typed margin | wins |
|---|---|---|---|---|
| CHAT_COMPLETION | 0.6121 | 40/40 | 0.6567 | 40/40 |
| CRYPTO_PRICE | 0.0822 | 51/60 | 0.9916 | 60/60 |
| CURRENCY_EXCHANGE | 0.0712 | 33/40 | 0.9875 | 40/40 |
| FINANCIAL_DATA | 0.0470 | 30/40 | 1.0000 | 40/40 |
| GAS_PRICE | 0.0064 | 20/40 | 1.0000 | 40/40 |
| SSL_VERIFICATION | 0.0617 | 30/40 | 1.0000 | 40/40 |
| STOCK_PRICE | 0.1141 | 35/40 | 0.9875 | 40/40 |
| STRESS | 0.0741 | 11/14 | 0.9990 | 14/14 |
| TOKEN_HOLDER_COUNT | 0.1297 | 37/40 | 0.9875 | 40/40 |
| WEATHER_CHECK | 0.0994 | 38/40 | 0.9873 | 40/40 |

CHAT_COMPLETION is the control: prose falls through, so those scores should
match the baseline, and they do apart from the exact-match short circuit.

Two incidental findings about the baseline, both reproducible with the harness
below:

- It scores a **verbatim correct answer as low as 0.5170**. Telegraph's own
  promotion rules require `worst_self_match` ≥ 0.75, so by the documented
  criteria the reference module could not be promoted.
- On GAS_PRICE it ranks the good answer above the bad one **20 times out of
  40** — indistinguishable from chance.

## Reproducing

```bash
rustup target add wasm32-unknown-unknown
pip install wasmtime

# the candidate
cargo build --release --target wasm32-unknown-unknown --features real_weights

# the baseline, from telegraphprotocol/telegraph-wasm-baseline
cargo build --release --target wasm32-unknown-unknown --features real_weights

python bench.py <baseline.wasm> <candidate.wasm>
```

`bench.py` loads each `.wasm` the way the node does — writing the question,
ground truth and miner answer into the module's own linear memory via its
exported `alloc`, then calling `rank_answer` — and reports the four metrics
Telegraph uses to decide promotion.

## How it scores

`TAU` is the relative-error half-life. An answer off by `TAU` scores ~0.37; off
by `3 × TAU`, ~0.05. It is a build-time choice because one binary is registered
per intent anyway:

| Build | TAU | For |
|---|---|---|
| default | 0.005 | prices, rates, temperatures |
| `tol_exact` | 1e-9 | counts and IDs, where only exact is correct |
| `tol_loose` | 0.05 | volatile intents such as GAS_PRICE |

Measured against ground truth `1000.00`:

| Relative error | default | `tol_exact` | `tol_loose` |
|---|---|---|---|
| 0% | 1.0000 | 1.0000 | 1.0000 |
| 0.5% | 0.3679 | 0.0000 | 0.9048 |
| 3% | 0.0025 | 0.0000 | 0.5488 |
| 10% | 0.0000 | 0.0000 | 0.1353 |

Normalisations applied before comparing, each added because a stress case caught
the scorer getting a real answer wrong:

- **Scale** — `1.5M` = `1500000`
- **Units** — `25 gwei` = `0.000000025 ETH`
- **Locale** — `111.240,55` = `111240.55`; the decimal separator is inferred
  from the run rather than assumed
- **Unicode** — `U+2212` minus, Arabic-Indic and fullwidth digits
- **Percent** — `5%` = `0.05`
- **Currency** — `100 USD` ≠ `100 EUR`, rejected outright rather than scored as
  a perfect match

## Gaming resistance

The scorer picks **one** number: the value attached to a recognised answer key,
otherwise the first number present. It does not take whichever candidate scores
best. An answer that sprays a range of guesses therefore cannot have all of them
counted — `"between 88992 and 133488, possibly 111240.55"` scores 0.

Denomination is checked adjacent to the number, so quoting a correct magnitude
in the wrong currency (`Volume was 3418.90 ETH` against a USD ground truth)
scores 0 rather than 1.

## Known limitations

Stated rather than hidden. These score 0 today when they should score high:

- Spelled-out numbers — `"twenty-five gwei"`
- Fractions — `"1/2 ETH"`
- Space thousands separators — `"2 841 977"`

The last is deliberate: treating spaces as separators risks merging two
genuinely unrelated numbers, which is a worse failure than the one it fixes.

The benchmark is also mine, not Telegraph's. It was written to try to break the
scorer — good answers are not always bare numbers, and most bad answers contain
numbers, including near-misses 1.5% out — but it caught three real bugs across
three runs (a negation inversion, a JSON regression, a currency/unit collision).
Assume a fourth exists.

## Layout

```
telegraph-typed-scorer/
  src/numeric.rs   number extraction: scale, units, locale, currency
  src/typed.rs     dispatch, tolerance, boolean verdicts, hedge resistance
  src/lib.rs       entry point; ~10 lines changed from the baseline
  src/{embed,tokenizer,bm25,math,allocator}.rs   inherited unchanged
cases.py           the 394-case corpus
bench.py           head-to-head harness
vet.py             integrity checks: statelessness, harness sanity, hand-checked math
dist/              the three built binaries
REGISTRATION.md    hashes and on-chain registration steps
```

Forked from [telegraphprotocol/telegraph-wasm-baseline](https://github.com/telegraphprotocol/telegraph-wasm-baseline)
(MIT). The embedding, tokenizer, BM25 and math modules are theirs, unmodified.
