//! Numeric extraction with scale-, unit-, currency- and locale-awareness.
//!
//! The baseline scorer compares text by embedding similarity and word
//! overlap. Both are blind to magnitude: BM25 of "111240.55 USD" against
//! "111238.02" is exactly 0.0, because the tokeniser splits on
//! non-alphanumerics and the two strings then share no token at all. This
//! module recovers the actual numbers so they can be compared as numbers.
//!
//! Four normalisations matter in practice, each of which was added after a
//! stress case caught the scorer getting a real answer wrong:
//!
//! * **Scale suffixes** - `1.5M` and `1500000` are the same value.
//! * **Unit families** - `25 gwei` and `0.000000025 ETH` are the same value.
//! * **Locale** - `111.240,55` and `111240.55` are the same value. Digits
//!   outside ASCII and the Unicode minus sign `U+2212` are folded too; the
//!   latter is what many formatters emit for negative temperatures, and
//!   without it every correct sub-zero answer scored zero.
//! * **Currency** - `100 USD` and `100 EUR` are *not* the same value. This is
//!   tracked separately from magnitude so a denomination mismatch can be
//!   rejected outright rather than scored as a perfect match.

use alloc::string::String;
use alloc::vec::Vec;

/// A number parsed out of text.
///
/// `value` already has any attached scale suffix applied (`1.5M` becomes
/// 1_500_000). `unit` is kept separate because it is only resolved once both
/// sides of a comparison have been seen - see [`canonical`].
#[derive(Clone, Copy)]
pub struct Num {
    pub value: f64,
    pub unit: Option<f64>,
    /// Denomination stated immediately beside this number, if any. Index into
    /// [`CURRENCIES`].
    pub currency: Option<u8>,
}

/// Resolve a number to a comparable magnitude.
///
/// `fallback_unit` is the *other* side's unit. A miner answering a bare `25`
/// to a ground truth of `25 gwei` means gwei; assuming otherwise would score
/// a correct answer as off by nine orders of magnitude.
pub fn canonical(n: &Num, fallback_unit: Option<f64>) -> f64 {
    n.value * n.unit.or(fallback_unit).unwrap_or(1.0)
}

// ---------------------------------------------------------------------------
// Normalisation
// ---------------------------------------------------------------------------

/// Fold Unicode variants onto the ASCII forms the scanner understands.
///
/// Covers the several dash characters used as minus signs, non-breaking and
/// thin spaces, and the Arabic-Indic, Devanagari and fullwidth digit blocks.
fn normalize(s: &str) -> String {
    let mut out = String::new();
    for c in s.chars() {
        let cp = c as u32;
        let mapped = match c {
            '\u{2212}' | '\u{2013}' | '\u{2012}' | '\u{FE63}' | '\u{FF0D}' => '-',
            '\u{00A0}' | '\u{202F}' | '\u{2009}' => ' ',
            _ => {
                if (0x0660..=0x0669).contains(&cp) {
                    (b'0' + (cp - 0x0660) as u8) as char
                } else if (0x06F0..=0x06F9).contains(&cp) {
                    (b'0' + (cp - 0x06F0) as u8) as char
                } else if (0x0966..=0x096F).contains(&cp) {
                    (b'0' + (cp - 0x0966) as u8) as char
                } else if (0xFF10..=0xFF19).contains(&cp) {
                    (b'0' + (cp - 0xFF10) as u8) as char
                } else {
                    c
                }
            }
        };
        out.push(mapped);
    }
    out
}

/// Resolve `.` and `,` inside a digit run into a plain parseable number.
///
/// Which separator is the decimal point depends on locale, so it is inferred
/// from the run itself rather than assumed:
///
/// * Both present - the rightmost one is the decimal point, so `111.240,55`
///   reads as EU and `111,240.55` as US.
/// * Repeated - grouping, so `2,841,977` and `1.234.567` are thousands.
/// * A single comma with exactly three digits after it is grouping
///   (`1,234`); with any other count it is a decimal comma (`1,5`).
/// * A single period is a decimal point, the common case.
fn canonical_digits(run: &str) -> String {
    let b = run.as_bytes();
    let mut dots = 0usize;
    let mut commas = 0usize;
    let mut last_dot = None;
    let mut last_comma = None;
    for (i, &c) in b.iter().enumerate() {
        if c == b'.' {
            dots += 1;
            last_dot = Some(i);
        } else if c == b',' {
            commas += 1;
            last_comma = Some(i);
        }
    }

    let decimal: Option<u8> = if dots > 0 && commas > 0 {
        if last_dot > last_comma {
            Some(b'.')
        } else {
            Some(b',')
        }
    } else if commas > 0 {
        if commas > 1 {
            None
        } else {
            let pos = last_comma.unwrap_or(0);
            if b.len() - pos - 1 == 3 {
                None
            } else {
                Some(b',')
            }
        }
    } else if dots > 0 {
        if dots > 1 {
            None
        } else {
            Some(b'.')
        }
    } else {
        None
    };

    let mut out = String::new();
    for &c in b.iter() {
        if c.is_ascii_digit() {
            out.push(c as char);
        } else if Some(c) == decimal {
            out.push('.');
        }
    }
    out
}

// ---------------------------------------------------------------------------
// Scale and unit suffixes
// ---------------------------------------------------------------------------

/// Multiplier for a scale suffix written immediately after the digits, as in
/// `1.5M`. Only applied when attached, since a spaced `m` is more likely to
/// mean metres than mega.
fn attached_scale(b: u8) -> Option<f64> {
    match b {
        b'k' | b'K' => Some(1e3),
        b'M' => Some(1e6),
        b'b' | b'B' => Some(1e9),
        b'T' => Some(1e12),
        _ => None,
    }
}

/// Multiplier for a scale or unit word following the digits.
///
/// Returns `(multiplier, is_unit)`. Scale words fold into the value; unit
/// words are tracked separately so a bare answer can inherit them.
fn word_factor(w: &str) -> Option<(f64, bool)> {
    match w {
        "thousand" => Some((1e3, false)),
        "million" => Some((1e6, false)),
        "billion" => Some((1e9, false)),
        "trillion" => Some((1e12, false)),
        // Ethereum denominations, canonicalised to ETH.
        "wei" => Some((1e-18, true)),
        "gwei" | "nanoeth" => Some((1e-9, true)),
        "eth" | "ether" => Some((1.0, true)),
        _ => None,
    }
}

/// Read the scale or unit that follows the digits ending at `i`.
/// Returns the multiplier, whether it was a unit, and bytes consumed.
fn suffix_at(text: &str, i: usize) -> (f64, bool, usize) {
    let b = text.as_bytes();

    if i < b.len() {
        if let Some(m) = attached_scale(b[i]) {
            let next_is_alpha = i + 1 < b.len() && b[i + 1].is_ascii_alphabetic();
            if !next_is_alpha {
                return (m, false, 1);
            }
        }
    }

    let mut j = i;
    while j < b.len() && b[j] == b' ' {
        j += 1;
    }
    if j > i + 1 {
        return (1.0, false, 0);
    }
    let start = j;
    while j < b.len() && b[j].is_ascii_alphabetic() {
        j += 1;
    }
    if j > start && j - start <= 8 {
        let mut w = String::new();
        for &c in &b[start..j] {
            w.push(c.to_ascii_lowercase() as char);
        }
        if let Some((m, is_unit)) = word_factor(&w) {
            return (m, is_unit, j - i);
        }
    }
    (1.0, false, 0)
}

// ---------------------------------------------------------------------------
// Currency and percentage
// ---------------------------------------------------------------------------

/// Denominations that make two equal magnitudes mean different things.
const CURRENCIES: [&str; 16] = [
    "usd", "eur", "gbp", "jpy", "chf", "cad", "aud", "nzd", "sek", "mxn",
    "cny", "usdc", "usdt", "btc", "eth", "sol",
];

/// Identify a denomination written immediately after a number.
///
/// Adjacency is what makes this safe. An earlier version scanned the whole
/// answer for any currency code, which read the asset ticker in
/// `{"symbol":"ETH","price":3419.15}` as the denomination and rejected a
/// correct USD price outright.
fn currency_suffix(text: &str, i: usize) -> Option<u8> {
    let b = text.as_bytes();
    let mut j = i;
    while j < b.len() && (b[j] == b' ' || b[j] == b'"' || b[j] == b'\'') {
        j += 1;
    }
    let start = j;
    while j < b.len() && b[j].is_ascii_alphabetic() {
        j += 1;
    }
    if j > start && j - start <= 4 {
        let w = &text[start..j];
        for (k, code) in CURRENCIES.iter().enumerate() {
            if w.eq_ignore_ascii_case(code) {
                return Some(k as u8);
            }
        }
    }
    None
}

/// Identify a currency symbol written immediately before a number.
fn currency_prefix(text: &str, start: usize) -> Option<u8> {
    let b = text.as_bytes();
    let mut j = start;
    while j > 0 && b[j - 1] == b' ' {
        j -= 1;
    }
    let head = &text[..j];
    if head.ends_with('$') {
        return Some(0);
    }
    if head.ends_with('\u{20AC}') {
        return Some(1);
    }
    if head.ends_with('\u{00A3}') {
        return Some(2);
    }
    if head.ends_with('\u{00A5}') {
        return Some(3);
    }
    None
}

/// Whether a value is quoted as a percentage.
pub fn is_percent(text: &str) -> bool {
    text.contains('%')
}

// ---------------------------------------------------------------------------
// Extraction
// ---------------------------------------------------------------------------

/// Scan already-normalised text for numbers.
fn extract_norm(text: &str) -> Vec<Num> {
    let b = text.as_bytes();
    let mut out = Vec::new();
    let mut i = 0usize;

    while i < b.len() {
        let neg = b[i] == b'-' && i + 1 < b.len() && b[i + 1].is_ascii_digit();
        if !(b[i].is_ascii_digit() || neg) {
            i += 1;
            continue;
        }
        if neg {
            i += 1;
        }

        // Collect digits and any separator that sits between two digits, so a
        // trailing comma or full stop is left behind rather than consumed.
        let run_start = i;
        while i < b.len() {
            if b[i].is_ascii_digit() {
                i += 1;
            } else if (b[i] == b'.' || b[i] == b',')
                && i + 1 < b.len()
                && b[i + 1].is_ascii_digit()
            {
                i += 1;
            } else {
                break;
            }
        }
        let run = &text[run_start..i];

        // Exponent, only when well-formed.
        let mut expo = String::new();
        if i < b.len() && (b[i] == b'e' || b[i] == b'E') {
            let mut j = i + 1;
            if j < b.len() && (b[j] == b'+' || b[j] == b'-') {
                j += 1;
            }
            if j < b.len() && b[j].is_ascii_digit() {
                expo.push('e');
                if b[i + 1] == b'+' || b[i + 1] == b'-' {
                    expo.push(b[i + 1] as char);
                }
                let ds = j;
                while j < b.len() && b[j].is_ascii_digit() {
                    j += 1;
                }
                expo.push_str(&text[ds..j]);
                i = j;
            }
        }

        let mut buf = String::new();
        if neg {
            buf.push('-');
        }
        buf.push_str(&canonical_digits(run));
        buf.push_str(&expo);

        if let Ok(v) = buf.parse::<f64>() {
            // Look for a denomination *before* the suffix is consumed. ETH is
            // both a unit (in the gwei conversion table) and a currency code,
            // so checking only afterwards missed it entirely and let
            // "3418.90 ETH" match a USD ground truth perfectly.
            let cur_pre = currency_suffix(text, i);
            let (mult, is_unit, adv) = suffix_at(text, i);
            i += adv;
            let cur = cur_pre
                .or_else(|| currency_suffix(text, i))
                .or_else(|| currency_prefix(text, run_start));
            if is_unit {
                out.push(Num { value: v, unit: Some(mult), currency: cur });
            } else {
                out.push(Num { value: v * mult, unit: None, currency: cur });
            }
        }
    }
    out
}

/// Extract every number in `text`, in order of appearance.
pub fn extract(text: &str) -> Vec<Num> {
    extract_norm(&normalize(text))
}

/// Keys whose value is the answer proper, rather than metadata.
const ANSWER_KEYS: [&str; 14] = [
    "price", "value", "result", "answer", "amount", "rate", "count", "total",
    "balance", "score", "gas", "temperature", "temp", "usd",
];

/// Pick the single number that represents the answer.
///
/// Prefers a value attached to a recognised answer key, so JSON carrying a
/// timestamp and a confidence alongside the price still resolves to the
/// price. Otherwise takes the first number present.
///
/// Selecting one number this way - rather than taking whichever candidate
/// scores best - is what makes the scorer hedge-resistant. An answer that
/// sprays a range of guesses cannot have all of them counted.
pub fn select(text: &str) -> Option<Num> {
    let norm = normalize(text);
    let mut lower = String::new();
    for c in norm.chars() {
        lower.push(c.to_ascii_lowercase());
    }

    for key in ANSWER_KEYS.iter() {
        let mut from = 0usize;
        while from < lower.len() {
            let rel = match lower[from..].find(key) {
                Some(r) => r,
                None => break,
            };
            let at = from + rel + key.len();
            if at >= norm.len() {
                break;
            }
            let tail = &norm[at..];
            let mut sep = 0usize;
            for c in tail.chars() {
                if sep >= 4 {
                    break;
                }
                if c == '"' || c == '\'' || c == ':' || c == '=' || c == ' ' {
                    sep += c.len_utf8();
                } else {
                    break;
                }
            }
            let rest = &tail[sep..];
            let starts_numeric = rest
                .as_bytes()
                .first()
                .map(|b| b.is_ascii_digit() || *b == b'-')
                .unwrap_or(false);
            if starts_numeric {
                if let Some(first) = extract_norm(rest).first() {
                    return Some(*first);
                }
            }
            from = at;
        }
    }

    extract_norm(&norm).first().copied()
}
