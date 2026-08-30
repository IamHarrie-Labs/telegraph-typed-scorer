"""Head-to-head scorer benchmark, replicating Telegraph's Stage 2 promotion test.

Loads two .wasm scoring modules the same way the node does - writing the
question / ground truth / miner answer into each module's own linear memory
via its exported `alloc`, then calling `rank_answer` - and reports the metrics
the node uses to decide whether a candidate replaces the champion.

Usage:  python bench.py <baseline.wasm> <candidate.wasm>
"""

import sys
import statistics
from collections import defaultdict
from wasmtime import Store, Module, Instance, Engine

import cases


class Scorer:
    """One loaded .wasm scoring module."""

    def __init__(self, path):
        self.engine = Engine()
        self.store = Store(self.engine)
        mod = Module.from_file(self.engine, path)
        self.inst = Instance(self.store, mod, [])
        ex = self.inst.exports(self.store)
        self.alloc = ex["alloc"]
        self.rank = ex["rank_answer"]
        self.mem = ex["memory"]

    def _put(self, s):
        data = s.encode("utf-8")
        ptr = self.alloc(self.store, len(data))
        self.mem.write(self.store, data, ptr)
        return ptr, len(data)

    def score(self, question, ground_truth, answer):
        qp, ql = self._put(question)
        gp, gl = self._put(ground_truth)
        ap, al = self._put(answer)
        return float(self.rank(self.store, qp, ql, gp, gl, ap, al))


def evaluate(scorer, corpus, label):
    rows = []
    allscores, selfs = [], []
    for n, (intent, q, gt, good, bad, fam) in enumerate(corpus):
        if n % 40 == 0:
            print(f"  {label}: {n}/{len(corpus)}", file=sys.stderr)
        g = scorer.score(q, gt, good)
        b = scorer.score(q, gt, bad)
        s = scorer.score(q, gt, gt)
        rows.append((intent, fam, g, b, g > b))
        allscores += [g, b]
        selfs.append(s)
    return {
        "rows": rows,
        "margin": statistics.fmean(g - b for _, _, g, b, _ in rows),
        "wins": sum(1 for r in rows if r[4]),
        "n": len(rows),
        "worst_self_match": min(selfs),
        "stddev": statistics.pstdev(allscores),
    }


def by_key(rows, idx):
    d = defaultdict(list)
    for r in rows:
        d[r[idx]].append(r)
    return d


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)

    corpus = cases.all_cases()
    print(f"corpus: {len(corpus)} cases\n", file=sys.stderr)
    base = evaluate(Scorer(sys.argv[1]), corpus, "baseline")
    cand = evaluate(Scorer(sys.argv[2]), corpus, "candidate")

    print()
    print("PER-INTENT".center(78, " "))
    print(f"{'intent':<22}{'baseline margin':>17}{'wins':>10}{'cand margin':>15}{'wins':>10}")
    print("-" * 78)
    bi, ci = by_key(base["rows"], 0), by_key(cand["rows"], 0)
    regressions = []
    for intent in sorted(bi):
        bm = statistics.fmean(g - b for _, _, g, b, _ in bi[intent])
        cm = statistics.fmean(g - b for _, _, g, b, _ in ci[intent])
        bw = sum(1 for r in bi[intent] if r[4])
        cw = sum(1 for r in ci[intent] if r[4])
        n = len(bi[intent])
        flag = ""
        if cm < bm - 1e-6 or cw < bw:
            flag = "  <-- REGRESSION"
            regressions.append(intent)
        print(f"{intent:<22}{bm:>17.4f}{str(bw)+'/'+str(n):>10}{cm:>15.4f}{str(cw)+'/'+str(n):>10}{flag}")

    print()
    print("CANDIDATE FAILURES BY FAMILY".center(78, " "))
    print(f"{'family':<28}{'losses':>10}{'of':>6}")
    print("-" * 78)
    cf = by_key(cand["rows"], 1)
    any_fail = False
    for fam in sorted(cf):
        losses = sum(1 for r in cf[fam] if not r[4])
        if losses:
            any_fail = True
            print(f"{fam:<28}{losses:>10}{len(cf[fam]):>6}")
    if not any_fail:
        print("  (none - candidate ranked good above bad on every case)")

    print()
    print(f"{'metric':<22}{'baseline':>12}{'candidate':>12}   gate")
    print("-" * 78)
    print(f"{'candidate_margin':<22}{base['margin']:>12.4f}{cand['margin']:>12.4f}   >= baseline")
    print(f"{'wins':<22}{str(base['wins'])+'/'+str(base['n']):>12}{str(cand['wins'])+'/'+str(cand['n']):>12}   >= baseline")
    print(f"{'worst_self_match':<22}{base['worst_self_match']:>12.4f}{cand['worst_self_match']:>12.4f}   >= 0.75")
    print(f"{'score_stddev':<22}{base['stddev']:>12.4f}{cand['stddev']:>12.4f}   above floor")

    passed = (
        cand["margin"] >= base["margin"]
        and cand["wins"] >= base["wins"]
        and cand["worst_self_match"] >= 0.75
        and cand["stddev"] > 0.01
        and not regressions
    )
    print()
    print("PROMOTION:", "WOULD PASS" if passed else "WOULD FAIL")
    if regressions:
        print("regressed intents:", ", ".join(regressions))


if __name__ == "__main__":
    main()
