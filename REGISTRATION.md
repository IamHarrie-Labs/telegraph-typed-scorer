# Registration manifest

Three binaries, one crate. Each is registered separately, for one intent, with
its own `registrationId`. Nothing here has been registered on-chain yet.

## Binaries

| File | Feature | TAU | Intended intents |
|---|---|---|---|
| `dist/typed-scorer-default.wasm` | `real_weights` | 0.005 | CRYPTO_PRICE, CURRENCY_EXCHANGE, FINANCIAL_DATA |
| `dist/typed-scorer-tol_exact.wasm` | `real_weights,tol_exact` | 1e-9 | TOKEN_HOLDER_COUNT, ONCHAIN_TX_LOOKUP |
| `dist/typed-scorer-tol_loose.wasm` | `real_weights,tol_loose` | 0.05 | GAS_PRICE |

### Target selection — checked at epoch 294

Only go after intents whose scoring is visibly broken. Two intents that were on
an earlier version of this list now have healthy champions and should be left
alone: **STOCK_PRICE** (top score 0.9947) and **WEATHER_CHECK** (0.9728). A
working incumbent is a real fight; a flatlined one is not.

| Intent | Miners | Top score | Verdict |
|---|---|---|---|
| GAS_PRICE | 8 | 0.000000 | best target |
| CRYPTO_PRICE | 13 | 0.000004 | strong target, most miners |
| TOKEN_HOLDER_COUNT | 4 | 0.000049 | strong target, least competition |
| CURRENCY_EXCHANGE | 7 | 0.000034 | strong target |
| SSL_VERIFICATION | 6 | 0.007920 | good target (boolean path) |
| FINANCIAL_DATA | 8 | 0.068522 | good target |
| STOCK_PRICE | 6 | 0.9946 | **skip** — working champion |
| WEATHER_CHECK | 10 | 0.9728 | **skip** — working champion |

Note that `txlens` shows as "#1 in GAS PRICE" on the console while scoring
0.000000. Rank there is arbitrary: every miner on that intent is tied at zero,
which is the whole argument for replacing its scorer.

TAU is the relative-error half-life: an answer off by TAU scores ~0.37, off by
3×TAU scores ~0.05. `tol_exact` accepts only exact matches, which is correct for
holder counts and transaction values. `tol_loose` tolerates the genuine drift
between ground-truth capture and answer on a volatile intent.

Verified behaviour (ground truth 1000.00):

| Relative error | default | tol_exact | tol_loose |
|---|---|---|---|
| 0% | 1.0000 | 1.0000 | 1.0000 |
| 0.0001% | 0.9998 | 0.0000 | 1.0000 |
| 0.5% | 0.3679 | 0.0000 | 0.9048 |
| 3% | 0.0025 | 0.0000 | 0.5488 |
| 10% | 0.0000 | 0.0000 | 0.1353 |

## Hashes

`registerWasm` takes the **keccak256** of the exact bytes hosted. The node
re-downloads the file and re-hashes it; a mismatch is rejected. Do not let the
host re-encode the file after upload.

```
typed-scorer-default.wasm    24214165 bytes
  keccak256  0x4fc258c5037e920b7b363539e958ea54045dc58e9e9667df054f5e27a6fa60e9
  sha256     eb69c6e97807c27d661a6d87d1cda09105a561bbc1812aec95845dec3b28d51f

typed-scorer-tol_exact.wasm  24214165 bytes
  keccak256  0x210a4420c3363e15e62fed3ddc85e8104014a9fe52523b43f675631e20da5cf0
  sha256     b74a4af4f6616eb6e6d7b38b2c2dd9ce04267e097933796530281dce6edcfa60

typed-scorer-tol_loose.wasm  24214165 bytes
  keccak256  0xba022c2175baf6b1e872a1fe7dfd55e6e89791d4462c317fc0c5c0d02d5923e3
  sha256     308104639669566973c91268914c4d841c72f790d6041c4cf307f7ea58f1f51a
```

Identical sizes are expected: the only difference between the three is one
`f64` constant, which does not change the instruction count. The keccak256
hashes differ, and the tolerance table above confirms they behave differently.

Recompute at any time:

```bash
python -c "from Crypto.Hash import keccak;k=keccak.new(digest_bits=256);k.update(open('dist/typed-scorer-default.wasm','rb').read());print('0x'+k.hexdigest())"
```

## Pre-flight checks (all passing)

- 0 imports — no WASI, instantiates in the sandbox
- exports `alloc`, `dealloc`, `rank_answer`, `memory`
- blank and whitespace-only answers score exactly `0.0`
- verbatim correct answer scores exactly `1.0` (`worst_self_match` = 1.0000)
- 48 KB answers and emoji / CJK / Arabic-Indic text do not trap
- 24.2 MB, against the 32 MB cap

## Hosting — blocked, needs your credentials

The file must sit at a public `https://` or `ipfs://` URL the node can fetch.
I cannot upload it: Pinata needs `PINATA_API_KEY` / `PINATA_API_SECRET`, and
publishing to a public host is your call to make, not mine.

Either:

1. **Pinata** — sign in at app.pinata.cloud, upload the `.wasm`, take the CID.
   The gateway URL `https://gateway.pinata.cloud/ipfs/<CID>` is what other
   registrations on this network use.
2. **Any static host** — GitHub raw, S3, your own domain. One live module is
   already served from a plain `https://` host, so this is accepted.

After upload, **re-hash what the host actually serves** and confirm it matches
the table above before registering.

## Registering

Easy path: submit at [integrate.telegraphprotocol.com](https://integrate.telegraphprotocol.com/),
which hashes the file and sends the transaction.

Direct path, one call on the Diamond:

```solidity
registerWasm(wasmHash, wasmUrl, intent)
```

- Network: Base Sepolia (chain 84532)
- Diamond: `0xac683bFa8F1C892E23e8300d14c20678C6FC0CA3`
- Cost: gas only. No bond, no fee.
- Returns a `registrationId` — keep it; it is how you check status and
  deregister.

Status moves `pending` → `active` / `rejected`. Expect a few minutes while the
node downloads and runs the Stage 2 benchmark.

One binary may be registered once per address. Registering the same file for a
*different* intent is a separate registration and is fine.

## Suggested order

Start with **GAS_PRICE** using `tol_loose`. It is the weakest incumbent measured
locally (20/40, indistinguishable from chance) and the live leaderboard has
shown its top miner at 0.000000. If a promotion is going to succeed anywhere, it
is there — and a single confirmed promotion is worth more as evidence than three
pending ones.
