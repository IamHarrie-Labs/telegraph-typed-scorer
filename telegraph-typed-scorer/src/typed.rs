//! Typed dispatch: score by value when the answer has a type, otherwise
//! defer to the inherited semantic scorer.
//!
//! This is the whole design. [`try_score`] returns `Some(score)` only when
//! the ground truth is confidently typed - a bare number, or an explicit
//! yes/no. Everything else returns `None`, and the caller falls through to
//! the unmodified baseline composite.
//!
//! That fallback is deliberate and load-bearing. Telegraph promotes a
//! candidate module only if it separates good answers from bad at least as
//! well as the incumbent, measured over a benchmark set the author cannot
//! see. By leaving prose scoring untouched, this module can only match or
//! beat the baseline on prose, never lose to it, and the typed path is pure
//! upside on the cases the baseline scores at its floor.

use alloc::string::String;
use alloc::vec::Vec;

use crate::numeric;

/// Relative-error half-life. A miner whose answer is off by `TAU` (as a
/// fraction of the true value) scores about 0.37; off by `3 * TAU`, about
/// 0.05.
///
/// The right tolerance is intent-specific, so it is a build-time choice:
/// TOKEN_HOLDER_COUNT is exact-or-nothing, CRYPTO_PRICE moves a little
/// between the ground-truth capture and the answer, and GAS_PRICE can move a
/// lot. One binary is registered per intent anyway, so this costs nothing.
#[cfg(feature = "tol_exact")]
pub const TAU: f64 = 0.004;
#[cfg(feature = "tol_loose")]
pub const TAU: f64 = 0.006;
#[cfg(not(any(feature = "tol_exact", feature = "tol_loose")))]
pub const TAU: f64 = 0.006;

/// Ground truths longer than this many alphabetic words are treated as prose
/// and left to the semantic scorer, even if they contain a number. Keeps
/// "the population grew through 2019 across every measured sector" out of
/// the numeric path.

/// Candidate numbers allowed before an answer is considered to be padding
/// its chances. Normal structured answers carry a handful (value, timestamp,
/// confidence); a long list of guesses is something else.
const FREE_CANDIDATES: usize = 5;

/// Count whitespace-delimited tokens that are purely alphabetic and at least
/// two characters long.
fn alpha_word_count(s: &str) -> usize {
    let mut n = 0;
    for tok in s.split(|c: char| !c.is_alphanumeric()) {
        if tok.len() >= 2 && tok.chars().all(|c| c.is_ascii_alphabetic()) {
            n += 1;
        }
    }
    n
}

/// Vocabulary for boolean verdicts.
///
/// Matched as whole words, never as substrings. Substring matching is what
/// made an earlier version score "No, the certificate has expired" as a
/// positive verdict: "no" appears inside "not", and inside "know".
const POSITIVE: [&str; 10] = [
    "yes", "true", "valid", "authentic", "genuine", "real", "safe",
    "trusted", "secure", "legitimate",
];
const NEGATIVE: [&str; 11] = [
    "no", "false", "invalid", "fake", "deepfake", "manipulated", "expired",
    "revoked", "untrusted", "malicious", "forged",
];
/// Tokens that invert the verdict word that follows them. "isn" and "doesn"
/// appear because the apostrophe splits "isn't" into two tokens.
const NEGATORS: [&str; 7] = [
    "not", "isn", "doesn", "never", "cannot", "without", "failed",
];

/// How many words a negation reaches forward.
const NEGATION_WINDOW: usize = 4;

/// Split into lowercase alphanumeric words, flagging those that act as
/// structural keys rather than content.
///
/// A token is a key when a colon or equals follows it (allowing for a closing
/// quote), as in `{"valid":false}`. Without this distinction the key `valid`
/// is read as the verdict and the value `false` never gets looked at, so
/// `{"valid":false}` and `{"valid":true}` score identically.
fn words_with_keyflag(s: &str) -> Vec<(String, bool)> {
    let b = s.as_bytes();
    let mut out = Vec::new();
    let mut i = 0usize;
    while i < b.len() {
        if !b[i].is_ascii_alphanumeric() {
            i += 1;
            continue;
        }
        let start = i;
        while i < b.len() && b[i].is_ascii_alphanumeric() {
            i += 1;
        }
        let mut w = String::new();
        for &c in &b[start..i] {
            w.push(c.to_ascii_lowercase() as char);
        }
        let mut j = i;
        if j < b.len() && (b[j] == b'"' || b[j] == b'\'') {
            j += 1;
        }
        let is_key = j < b.len() && (b[j] == b':' || b[j] == b'=');
        out.push((w, is_key));
    }
    out
}

/// Read a boolean ground truth, if that is all it is.
///
/// Requires the ground truth to be a single verdict word, so a sentence that
/// merely contains "no" is left to the semantic scorer.
fn polarity(s: &str) -> Option<bool> {
    let words = words_with_keyflag(s);
    if words.len() != 1 {
        return None;
    }
    let w = words[0].0.as_str();
    if POSITIVE.iter().any(|p| *p == w) {
        return Some(true);
    }
    if NEGATIVE.iter().any(|p| *p == w) {
        return Some(false);
    }
    None
}

/// Find the verdict a miner's answer asserts, if any.
///
/// Scans left to right and returns the first verdict word found, flipped if a
/// negator appeared within the preceding few words. So "the certificate is
/// not valid" reads negative, and "it is not expired" reads positive. Tokens
/// used as keys are skipped, so the verdict comes from the value.
fn answer_polarity(s: &str) -> Option<bool> {
    let mut negate_for = 0usize;
    for (w, is_key) in words_with_keyflag(s).iter() {
        if *is_key {
            continue;
        }
        let ws = w.as_str();
        if NEGATORS.iter().any(|n| *n == ws) {
            negate_for = NEGATION_WINDOW;
            continue;
        }
        let negated = negate_for > 0;
        if POSITIVE.iter().any(|p| *p == ws) {
            return Some(!negated);
        }
        if NEGATIVE.iter().any(|p| *p == ws) {
            return Some(negated);
        }
        if negate_for > 0 {
            negate_for -= 1;
        }
    }
    None
}

/// Convert a relative error into a score in [0, 1].
fn from_relative_error(rel: f64) -> f32 {
    if rel <= 0.0 {
        return 1.0;
    }
    let s = libm::exp(-rel / TAU);
    if s.is_finite() {
        s as f32
    } else {
        0.0
    }
}

/// Score `miner_answer` against `ground_truth` by value, or return `None` to
/// let the semantic scorer handle it.
///
/// The caller is responsible for rejecting blank answers before this point.
/// How the caller should use a typed assessment.
pub enum Verdict {
    /// Use this score directly. The ground truth is a bare value, so the
    /// numeric or boolean comparison is the whole answer.
    Pure(f32),
    /// Blend this numeric score with the semantic composite. The ground truth
    /// is a sentence that contains a number, so both signals carry meaning.
    ///
    /// This case exists because Telegraph's own benchmarks state ground truth
    /// as prose - "the current gas price is approximately 25 gwei" - rather
    /// than as a bare value. Refusing the numeric path there dropped
    /// separation from 1.00 to 0.05 and lost a registration.
    Blend(f32),
    /// Nothing typed to say; use the semantic composite alone.
    Semantic,
}

/// Ground truths longer than this are prose. They still get a numeric reading
/// when they contain a number, but blended rather than pure.
const PROSE_ALPHA_WORDS: usize = 4;

pub fn assess(ground_truth: &str, miner_answer: &str) -> Verdict {
    // --- Boolean path -----------------------------------------------------
    // Only fires on a ground truth that is literally yes/no/true/false, so a
    // sentence that merely contains "no" is left alone.
    if let Some(truth) = polarity(ground_truth) {
        return match answer_polarity(miner_answer) {
            Some(a) if a == truth => Verdict::Pure(1.0),
            Some(_) => Verdict::Pure(0.0),
            None => Verdict::Semantic,
        };
    }

    // --- Numeric path -----------------------------------------------------
    let is_prose = alpha_word_count(ground_truth) > PROSE_ALPHA_WORDS;
    let truth = match numeric::select(ground_truth) {
        Some(t) => t,
        None => return Verdict::Semantic,
    };

    // Ground truth is numeric, so an answer with no number in it is wrong -
    // not merely unlike the truth. This is the case the baseline rewards
    // most perversely, giving a long numberless paragraph its full length
    // bonus.
    let cand = match numeric::select(miner_answer) {
        Some(c) => c,
        // A bare-value question answered without any number is simply wrong.
        // A prose question is not: the answer may be correct and merely omit
        // the figure, so let the semantic scorer judge it rather than
        // punishing it to zero.
        // A numeric question answered with no figure at all is not answered.
        // Sending these to the semantic scorer was too lenient: it let a
        // fluent, numberless non-answer keep a mid-range score and collapsed
        // the separation the promotion gate measures.
        None => return if is_prose { Verdict::Semantic } else { Verdict::Pure(0.0) },
    };

    // Denomination mismatch: equal magnitudes quoted in different currencies
    // are not the same answer. Only rejected when both sides state one, so a
    // bare answer still inherits the ground truth's denomination.
    if let (Some(t_cur), Some(a_cur)) = (truth.currency, cand.currency) {
        if t_cur != a_cur {
            return Verdict::Pure(0.0);
        }
    }

    let t = numeric::canonical(&truth, None);
    let mut a = numeric::canonical(&cand, truth.unit);

    // Percentage alignment: "5%" and "0.05" are the same quantity stated two
    // ways, and only one side may carry the sign.
    let t_pct = numeric::is_percent(ground_truth);
    let a_pct = numeric::is_percent(miner_answer);
    if t_pct && !a_pct {
        a *= 100.0;
    } else if !t_pct && a_pct {
        a /= 100.0;
    }

    let denom = if t.abs() > 1e-12 { t.abs() } else { 1.0 };
    let rel = (a - t).abs() / denom;
    let mut score = from_relative_error(rel);

    // Mild dilution for answers carrying an unusual number of candidates.
    // Selection already takes a single number, so this only discourages
    // burying a guess in a long list.
    let count = numeric::extract(miner_answer).len();
    if count > FREE_CANDIDATES {
        let extra = (count - FREE_CANDIDATES) as f64;
        score = (score as f64 / (1.0 + 0.35 * extra)) as f32;
    }

    let score = if score > 1.0 {
        1.0
    } else if score < 0.0 || !score.is_finite() {
        0.0
    } else {
        score
    };

    if is_prose {
        Verdict::Blend(score)
    } else {
        Verdict::Pure(score)
    }
}
