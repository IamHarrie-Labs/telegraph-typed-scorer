"""Benchmark corpus: ~40 good/bad answer pairs per intent.

Cases are generated from a table of facts crossed with a fixed set of answer
*shapes*, so coverage of formatting variation is systematic rather than
whatever happened to come to mind. Every case is tagged with a `family` so
the report can show which shape a scorer fails on.

Two rules keep this honest:

* Good answers are not always bare numbers. They include comma formatting,
  currency symbols, JSON with distracting metadata, prose wrappers, and
  unit-converted equivalents.
* Bad answers are not always numberless prose. Most of them contain numbers,
  including near-misses just outside tolerance, which is the case a
  magnitude-aware scorer could plausibly get wrong.

Families beginning `adv_` are adversarial towards the typed scorer
specifically - they are the ones expected to expose its weaknesses.
"""

# --------------------------------------------------------------------------
# Facts: (question, value, unit, decimals)
# --------------------------------------------------------------------------

CRYPTO = [
    ("What is the current price of Bitcoin?", 111240.55, "USD", 2),
    ("What is the price of Ethereum right now?", 3418.90, "USD", 2),
    ("What is Solana trading at?", 184.22, "USD", 2),
    ("What is the current price of Cardano?", 0.8134, "USD", 4),
    ("What is XRP trading at today?", 2.4471, "USD", 4),
    ("What is the price of Dogecoin?", 0.1932, "USD", 4),
    ("What is Chainlink trading at?", 21.87, "USD", 2),
    ("What is the current price of Avalanche?", 42.15, "USD", 2),
    ("What is Polkadot trading at?", 7.63, "USD", 2),
    ("What is the price of Litecoin?", 118.44, "USD", 2),
]

STOCK = [
    ("What is the current share price of NVIDIA?", 178.35, "USD", 2),
    ("What is Apple stock trading at?", 241.80, "USD", 2),
    ("What is the share price of Microsoft?", 468.12, "USD", 2),
    ("What is Tesla trading at?", 389.55, "USD", 2),
    ("What is the current price of Amazon stock?", 221.90, "USD", 2),
    ("What is Alphabet stock trading at?", 192.44, "USD", 2),
    ("What is the share price of Meta?", 612.30, "USD", 2),
    ("What is AMD trading at?", 128.75, "USD", 2),
    ("What is the current share price of Intel?", 24.18, "USD", 2),
    ("What is Netflix stock trading at?", 891.60, "USD", 2),
]

FX = [
    ("What is the EUR to USD exchange rate?", 1.0842, "USD", 4),
    ("What is the GBP to USD exchange rate?", 1.2694, "USD", 4),
    ("What is the USD to JPY exchange rate?", 151.38, "JPY", 2),
    ("What is the USD to CHF exchange rate?", 0.8817, "CHF", 4),
    ("What is the AUD to USD exchange rate?", 0.6543, "USD", 4),
    ("What is the USD to CAD exchange rate?", 1.4021, "CAD", 4),
    ("What is the NZD to USD exchange rate?", 0.5988, "USD", 4),
    ("What is the USD to SEK exchange rate?", 10.9433, "SEK", 4),
    ("What is the EUR to GBP exchange rate?", 0.8541, "GBP", 4),
    ("What is the USD to MXN exchange rate?", 20.1477, "MXN", 4),
]

HOLDERS = [
    ("How many holders does the USDC contract have?", 2841977, "", 0),
    ("How many holders does the USDT contract have?", 6204531, "", 0),
    ("How many addresses hold LINK?", 748219, "", 0),
    ("How many holders does the UNI token have?", 412903, "", 0),
    ("How many addresses hold SHIB?", 1502884, "", 0),
    ("How many holders does the PEPE contract have?", 268447, "", 0),
    ("How many addresses hold AAVE?", 189336, "", 0),
    ("How many holders does the MKR token have?", 96712, "", 0),
    ("How many addresses hold CRV?", 143508, "", 0),
    ("How many holders does the ENS token have?", 812440, "", 0),
]

WEATHER = [
    ("What is the current temperature in Reykjavik?", -4.5, "C", 1),
    ("What is the temperature in Oslo right now?", -12.3, "C", 1),
    ("What is the current temperature in Cairo?", 31.8, "C", 1),
    ("What is the temperature in Singapore?", 29.4, "C", 1),
    ("What is the current temperature in Moscow?", -18.7, "C", 1),
    ("What is the temperature in Sydney right now?", 26.1, "C", 1),
    ("What is the current temperature in Toronto?", -6.2, "C", 1),
    ("What is the temperature in Nairobi?", 22.9, "C", 1),
    ("What is the current temperature in Anchorage?", -21.4, "C", 1),
    ("What is the temperature in Lisbon right now?", 16.5, "C", 1),
]

# Gas is kept separate: its good answers exercise unit conversion.
GAS = [
    ("What is the current gas price on Ethereum mainnet?", 25.0),
    ("What is the base fee on Ethereum?", 18.0),
    ("What is the current gas price on Ethereum?", 42.5),
    ("What is the priority fee on Ethereum right now?", 2.5),
    ("What is the current base fee on mainnet?", 11.3),
    ("What is the gas price on Ethereum mainnet now?", 63.8),
    ("What is the current priority fee?", 1.2),
    ("What is the base fee on Ethereum mainnet?", 34.6),
    ("What is the gas price right now on Ethereum?", 8.9),
    ("What is the current Ethereum gas price?", 57.1),
]

# Revenue figures exercise scale words and suffixes.
FINANCIALS = [
    ("What was Apple's revenue last quarter?", 94.93),
    ("What was Microsoft's quarterly revenue?", 65.58),
    ("What was Alphabet's revenue last quarter?", 88.27),
    ("What was Amazon's quarterly revenue?", 158.88),
    ("What was Meta's revenue last quarter?", 40.59),
    ("What was NVIDIA's quarterly revenue?", 35.08),
    ("What was Tesla's revenue last quarter?", 25.18),
    ("What was Intel's quarterly revenue?", 13.28),
    ("What was Netflix's revenue last quarter?", 9.83),
    ("What was AMD's quarterly revenue?", 6.82),
]

# Numberless but fluent and on-topic. These are what the baseline over-rewards.
FLUFF = {
    "CRYPTO_PRICE": "Cryptocurrency valuations move continuously across global exchanges, driven by shifting liquidity, sentiment and trading volume throughout the day.",
    "STOCK_PRICE": "Equity prices reflect investor expectations about future earnings and change throughout each trading session as new information reaches the market.",
    "CURRENCY_EXCHANGE": "Foreign exchange rates are set by interbank markets and fluctuate constantly in response to interest rate differentials and capital flows.",
    "TOKEN_HOLDER_COUNT": "The number of distinct addresses holding a token grows over time as distribution widens across exchanges, custodians and retail wallets.",
    "WEATHER_CHECK": "Local temperature depends on latitude, elevation, prevailing wind and the time of day, and changes measurably over the course of an afternoon.",
    "GAS_PRICE": "Gas prices on Ethereum rise and fall with network congestion and are denominated in gwei per unit of gas consumed by a transaction.",
    "FINANCIAL_DATA": "Quarterly revenue reflects performance across the company's operating segments and is reported in its consolidated financial statements.",
}


def _fmt(v, dec):
    """Format with thousands separators at the given precision."""
    return f"{v:,.{dec}f}" if dec else f"{int(v):,}"


def _numeric_cases(intent, facts):
    """Cross each fact with four (good, bad) shape pairs."""
    out = []
    for q, val, unit, dec in facts:
        plain = _fmt(val, dec).replace(",", "")
        commas = _fmt(val, dec)
        near = val * 1.015          # 1.5% out - wrong, but plausibly close
        far = val * 1.42            # clearly wrong
        tenx = val * 10             # magnitude error

        out += [
            # bare value vs numberless fluff
            (intent, q, f"{plain} {unit}".strip(), plain, FLUFF[intent], "plain_vs_fluff"),

            # comma/symbol formatting vs a near-miss that is genuinely wrong
            (intent, q, f"{plain} {unit}".strip(),
             (f"${commas}" if unit == "USD" else f"{commas} {unit}".strip()),
             f"{_fmt(near, dec)} {unit}".strip(),
             "formatted_vs_near_miss"),

            # JSON carrying distracting metadata vs a magnitude error
            (intent, q, f"{plain} {unit}".strip(),
             '{"value":%s,"unit":"%s","ts":1735689600,"confidence":0.97}' % (plain, unit or "n/a"),
             f"{_fmt(tenx, dec)} {unit}".strip(),
             "json_vs_magnitude"),

            # prose-wrapped correct value vs prose-wrapped wrong value
            (intent, q, f"{plain} {unit}".strip(),
             f"Based on current data, the figure is {commas} {unit}.".strip(),
             f"Based on current data, the figure is {_fmt(far, dec)} {unit}.".strip(),
             "prose_vs_prose"),
        ]
    return out


def _gas_cases():
    """Gas exercises unit conversion: gwei, bare, and ETH-denominated."""
    out = []
    for q, gwei in GAS:
        eth = f"{gwei * 1e-9:.12f}".rstrip("0")
        out += [
            ("GAS_PRICE", q, f"{gwei:g} gwei", f"{gwei:g} gwei",
             FLUFF["GAS_PRICE"], "gwei_vs_fluff"),

            # bare number must inherit the ground truth's unit
            ("GAS_PRICE", q, f"{gwei:g} gwei", f"{gwei:g}",
             f"{gwei * 3.1:.1f} gwei", "bare_vs_wrong"),

            # unit-converted equivalent: the case the baseline cannot pass
            ("GAS_PRICE", q, f"{gwei:g} gwei", f"{eth} ETH",
             f"{gwei * 10:g} gwei", "ethunit_vs_magnitude"),

            ("GAS_PRICE", q, f"{gwei:g} gwei",
             '{"gas":%g,"unit":"gwei"}' % gwei,
             f"{gwei * 1.6:.1f} gwei", "json_vs_near"),
        ]
    return out


def _financial_cases():
    """Revenue exercises scale words and attached suffixes."""
    out = []
    for q, bn in FINANCIALS:
        full = bn * 1e9
        out += [
            ("FINANCIAL_DATA", q, f"{bn} billion USD", f"{bn}B",
             FLUFF["FINANCIAL_DATA"], "suffix_vs_fluff"),
            ("FINANCIAL_DATA", q, f"{bn} billion USD", f"{bn} billion",
             f"{bn * 1.35:.2f} billion", "word_vs_wrong"),
            ("FINANCIAL_DATA", q, f"{bn} billion USD", f"{full:,.0f}",
             f"{bn:.2f} million", "expanded_vs_uniterror"),
            ("FINANCIAL_DATA", q, f"{bn} billion USD",
             f"Revenue came in at {bn} billion dollars for the quarter.",
             f"Revenue came in at {bn * 0.55:.2f} billion dollars for the quarter.",
             "prose_vs_prose"),
        ]
    return out


# --------------------------------------------------------------------------
# Adversarial: aimed at the typed scorer's known weak points
# --------------------------------------------------------------------------

def _adversarial():
    out = []
    for q, val, unit, dec in CRYPTO[:5]:
        plain = _fmt(val, dec).replace(",", "")
        out += [
            # hedge that buries the truth mid-list; selection must not reward it
            ("CRYPTO_PRICE", q, f"{plain} {unit}",
             plain,
             f"It is likely between {val * 0.8:.2f} and {val * 1.2:.2f}, possibly {plain}, or perhaps {val * 1.1:.2f}.",
             "adv_hedge_buried"),

            # truth stated first, then hedged - defensible as correct
            ("CRYPTO_PRICE", q, f"{plain} {unit}",
             f"{plain}, though estimates vary between {val * 0.9:.2f} and {val * 1.1:.2f}.",
             FLUFF["CRYPTO_PRICE"],
             "adv_hedge_leading"),

            # correct value buried behind unrelated leading numbers
            ("CRYPTO_PRICE", q, f"{plain} {unit}",
             '{"rank":1,"marketcap":2200000000000,"price":%s}' % plain,
             '{"rank":1,"marketcap":2200000000000,"price":%s}' % f"{val * 1.4:.2f}",
             "adv_leading_distractors"),

            # very long answer containing the right value
            ("CRYPTO_PRICE", q, f"{plain} {unit}",
             ("Market commentary. " * 200) + f"The price is {plain} {unit}.",
             ("Market commentary. " * 200) + f"The price is {val * 1.5:.2f} {unit}.",
             "adv_long_answer"),
        ]
    return out


# --------------------------------------------------------------------------
# Prose controls: the candidate must not regress against the baseline here
# --------------------------------------------------------------------------

PROSE = [
    ("Explain what a blockchain is.",
     "A blockchain is a distributed ledger that records transactions across many computers so entries cannot be altered retroactively.",
     "A blockchain is a shared, append-only ledger replicated across many nodes, which makes past records practically impossible to change."),
    ("What causes inflation?",
     "Inflation is caused by rising demand relative to supply, increases in production costs, and growth in the money supply.",
     "Prices rise when demand outstrips supply, when input costs climb, or when the money supply expands faster than output."),
    ("Who wrote the novel Beloved?",
     "Toni Morrison wrote the novel Beloved, published in 1987.",
     "Beloved was written by Toni Morrison and appeared in 1987."),
    ("What is photosynthesis?",
     "Photosynthesis is the process by which plants convert light energy into chemical energy stored as sugars.",
     "Plants use photosynthesis to turn sunlight into chemical energy, storing it as carbohydrates."),
    ("Why is the sky blue?",
     "Sunlight scatters off air molecules, and shorter blue wavelengths scatter more than longer red ones.",
     "Air molecules scatter short blue wavelengths of sunlight more strongly than long red ones, so the sky looks blue."),
    ("What does a compiler do?",
     "A compiler translates source code written in one programming language into another, usually machine code.",
     "A compiler takes source code and turns it into a lower-level representation, typically machine instructions."),
    ("What is the function of the liver?",
     "The liver filters blood, metabolises nutrients and drugs, and produces bile for digestion.",
     "The liver cleans the blood, processes nutrients and medicines, and makes bile used in digestion."),
    ("How does a refrigerator work?",
     "A refrigerator moves heat outward by compressing and expanding a refrigerant that absorbs heat as it evaporates.",
     "Refrigerators pump heat out of the cabinet using a refrigerant that absorbs heat when it evaporates and releases it when compressed."),
    ("What caused the fall of the Roman Empire?",
     "The Roman Empire fell through a combination of military pressure, political instability and economic decline.",
     "Rome collapsed under sustained invasions, internal political turmoil and a weakening economy."),
    ("What is machine learning?",
     "Machine learning is a field where systems learn patterns from data rather than following explicitly written rules.",
     "Machine learning builds systems that infer patterns from examples instead of being programmed with fixed rules."),
]

DISTRACTORS = [
    "The Great Barrier Reef is the largest coral reef system, lying off the coast of Queensland in Australia.",
    "Mount Everest sits on the border between Nepal and Tibet and is the highest peak above sea level.",
    "The mitochondrion is the organelle that produces most of the chemical energy inside eukaryotic cells.",
    "Venice is built across a group of small islands in a lagoon in northeastern Italy.",
    "The violin family emerged in northern Italy during the sixteenth century and displaced earlier bowed instruments.",
]


def _prose_cases():
    out = []
    for i, (q, gt, para) in enumerate(PROSE):
        for k in range(4):
            if k == 0:
                good, fam = para, "paraphrase"
            elif k == 1:
                good, fam = gt, "verbatim"
            elif k == 2:
                good, fam = para + " This is well established.", "paraphrase_padded"
            else:
                good, fam = gt.rstrip(".") + ", broadly speaking.", "verbatim_hedged"
            bad = DISTRACTORS[(i + k) % len(DISTRACTORS)]
            out.append(("CHAT_COMPLETION", q, gt, good, bad, fam))
    return out



# --------------------------------------------------------------------------
# Boolean verdicts: exercises the polarity path, including negation phrasing
# --------------------------------------------------------------------------

SSL = [
    ("Is the SSL certificate for example.com valid?", True),
    ("Is the SSL certificate for expired.badssl.com valid?", False),
    ("Is the TLS certificate for github.com trusted?", True),
    ("Is the certificate for self-signed.badssl.com trusted?", False),
    ("Is the SSL certificate for cloudflare.com valid?", True),
    ("Is the certificate for revoked.badssl.com still valid?", False),
    ("Is the TLS certificate for wikipedia.org valid?", True),
    ("Is the certificate for untrusted-root.badssl.com trusted?", False),
    ("Is the SSL certificate for mozilla.org valid?", True),
    ("Is the certificate for wrong.host.badssl.com valid?", False),
]

# (positive phrasing, negative phrasing) per shape. Index 2 deliberately
# states the verdict through a negation, which is what broke an earlier
# substring-matching implementation.
BOOL_SHAPES = [
    ("yes", "no", "bare"),
    ("Yes, the certificate is valid and trusted.",
     "No, the certificate is invalid.", "sentence"),
    ("It is not expired, so the certificate is fine.",
     "The certificate is not valid.", "negation_phrased"),
    ('{"valid":true,"checked":1735689600}',
     '{"valid":false,"checked":1735689600}', "json"),
]


def _bool_cases():
    out = []
    for q, truth in SSL:
        gt = "yes" if truth else "no"
        for pos, neg, fam in BOOL_SHAPES:
            good, bad = (pos, neg) if truth else (neg, pos)
            out.append(("SSL_VERIFICATION", q, gt, good, bad, fam))
    return out



# --------------------------------------------------------------------------
# Stress: formats and traps that a magnitude-aware scorer can get wrong.
# Every entry here was a live failure at some point; they stay as regression
# tests. MINUS is U+2212, the character many formatters emit for negatives.
# --------------------------------------------------------------------------

MINUS = "−"
ARABIC = "٢٨٤١٩٧٧"   # 2841977
EURO = "€"

STRESS = [
    # (question, ground_truth, good, bad, family)
    ("What is the price of Bitcoin?", "111240.55 USD", "111.240,55",
     "91.240,55", "eu_decimal"),
    ("What is the price of Ethereum?", "3418.90 USD", "3.418,90",
     "5.418,90", "eu_decimal"),
    ("What is the price of Bitcoin?", "111240.55 USD", "111,240.55",
     "131,240.55", "us_decimal"),
    ("What is the current inflation rate?", "5%", "0.05", "0.09", "percent"),
    ("What is the current inflation rate?", "0.05", "5%", "9%", "percent"),
    ("What is the yield on the 10-year?", "4.25%", "4.25%", "6.10%", "percent"),
    ("How much is the fee?", "100 USD", "100 USD", "100 " + "EUR", "currency"),
    ("How much is the fee?", "100 USD", "$100", EURO + "100", "currency"),
    ("What is the price of Bitcoin?", "111240.55 USD",
     '{"symbol":"BTC","price":111240.55}', "Volume was 111240.55 BTC",
     "currency_role"),
    ("What is the price of Ethereum?", "3418.90 USD",
     '{"symbol":"ETH","price":3419.15}', "Volume was 3418.90 ETH",
     "currency_role"),
    ("What is the temperature in Reykjavik?", "-4.5 C", MINUS + "4.5 C",
     MINUS + "18.9 C", "unicode_minus"),
    ("What is the temperature in Oslo?", "-12.3 C", MINUS + "12.3 C",
     MINUS + "31.7 C", "unicode_minus"),
    ("What is the temperature in Moscow?", "-18.7 C", MINUS + "18.7 C",
     "18.7 C", "unicode_minus"),
    ("How many holders does USDC have?", "2841977", ARABIC, "9999999",
     "nonlatin_digits"),
]


def _stress_cases():
    return [("STRESS", q, gt, g, b, fam) for q, gt, g, b, fam in STRESS]


def all_cases():
    cases = []
    cases += _numeric_cases("CRYPTO_PRICE", CRYPTO)
    cases += _numeric_cases("STOCK_PRICE", STOCK)
    cases += _numeric_cases("CURRENCY_EXCHANGE", FX)
    cases += _numeric_cases("TOKEN_HOLDER_COUNT", HOLDERS)
    cases += _numeric_cases("WEATHER_CHECK", WEATHER)
    cases += _gas_cases()
    cases += _financial_cases()
    cases += _adversarial()
    cases += _bool_cases()
    cases += _stress_cases()
    cases += _prose_cases()
    return cases


if __name__ == "__main__":
    from collections import Counter
    c = all_cases()
    print(f"total cases: {len(c)}")
    for intent, n in sorted(Counter(x[0] for x in c).items()):
        print(f"  {intent:<22}{n:>4}")
