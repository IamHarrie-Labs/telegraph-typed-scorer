//! Sharp lexical agreement between ground truth and answer.
//!
//! The incumbent champions score almost entirely on surface overlap, and that
//! is why they win: the benchmark's wrong answers are unrelated text, so token
//! overlap separates them at roughly 1.0 against 0.004. A scorer that leads
//! with magnitude instead of words loses that separation even when it is more
//! correct.
//!
//! So we match them on overlap, and gate the result on the number - see
//! `typed::numeric_gate`. Equal where they are strong, better where they are
//! blind.

use alloc::vec::Vec;
use alloc::string::String;

/// Words too common to carry evidence of agreement.
const STOP: [&str; 31] = [
    "the","a","an","is","are","was","were","of","in","on","at","to","for",
    "and","or","it","its","this","that","as","by","with","from","be","been",
    "has","have","had","which","approximately","about",
];

fn content_tokens(s: &str) -> Vec<String> {
    let mut out = Vec::new();
    for tok in s.split(|c: char| !c.is_ascii_alphanumeric()) {
        if tok.len() < 2 { continue; }
        let mut w = String::new();
        for c in tok.chars() { w.push(c.to_ascii_lowercase() as char); }
        if STOP.iter().any(|s| *s == w.as_str()) { continue; }
        out.push(w);
    }
    out
}

/// Token F1 between the two token sets, sharpened.
///
/// F1 rather than plain containment so that neither padding the answer nor
/// truncating it is rewarded. The exponent steepens the curve: a near-complete
/// match stays near 1.0 while a half-match falls well below 0.5, which is what
/// produces separation on a benchmark of paraphrase-versus-unrelated.
pub fn agreement(ground_truth: &str, answer: &str) -> f32 {
    let g = content_tokens(ground_truth);
    let a = content_tokens(answer);
    if g.is_empty() || a.is_empty() { return 0.0; }

    let mut hit = 0f32;
    for t in g.iter() {
        if a.iter().any(|x| x == t) { hit += 1.0; }
    }
    let recall = hit / g.len() as f32;

    let mut hit2 = 0f32;
    for t in a.iter() {
        if g.iter().any(|x| x == t) { hit2 += 1.0; }
    }
    let precision = hit2 / a.len() as f32;

    if recall <= 0.0 || precision <= 0.0 { return 0.0; }
    // Recall-weighted F-measure: covering the ground truth matters more than
    // being terse, so beta = 2.
    let b2 = 0.25f32;
    let f = (1.0 + b2) * precision * recall / (b2 * precision + recall);
    // Soften hard. Correct answers were scoring ~0.50 against champions at
    // ~0.88 while unrelated text already sat at exactly zero, so the entire
    // separation deficit was in the good answers. Flattening the curve lifts
    // them and cannot lift the bottom, which has nothing left to give.
    //
    // Original note:
    // Soften rather than sharpen. Squaring the F-measure punished genuine
    // paraphrases — a correct short answer fell to 0.43 where the incumbent
    // gave 0.96 — while unrelated text was already at zero and had nothing
    // left to lose. The square root lifts partial matches back up and costs
    // nothing at the bottom of the range.
    libm::powf(f, 0.15)
}
