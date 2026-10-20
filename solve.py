"""DSO 429 HW3 solver: answers every unanswered round in questions.csv and writes answers/round-NNNN.json."""
import csv, io, json, re, sys, os, urllib.request
from datetime import date, datetime, timedelta

QURL = "https://raw.githubusercontent.com/FaisalXL/dso429-hourly-quiz/main/questions.csv"
NUM = r"-?[\d,]*\.?\d+"

def nums(s):
    return [float(x.replace(",", "")) for x in re.findall(NUM, s.replace("$", ""))]

def compute(q):
    t = q.replace("$", "")
    n = nums(t)
    if "compounded annually" in t:
        p, r, y = n[0], n[1], n[2]
        return p * (1 + r / 100) ** y
    if "gross margin" in t:
        return (n[0] - n[1]) / n[0] * 100
    if "headcount series" in t:
        s = re.search(r"runs (.*?)\. If", t).group(1)
        v = [float(x) for x in re.findall(NUM, s.replace(",", " "))]
        d = [v[i+1] - v[i] for i in range(len(v)-1)]
        if len(set(round(x, 6) for x in d)) == 1:
            return v[-1] + d[0]
        dd = [d[i+1] - d[i] for i in range(len(d)-1)]
        if len(set(round(x, 6) for x in dd)) == 1:
            return v[-1] + d[-1] + dd[0]
        if all(x != 0 for x in v):
            ratios = [v[i+1] / v[i] for i in range(len(v)-1)]
            if max(ratios) - min(ratios) < 1e-6:
                return v[-1] * ratios[0]
        if len(v) >= 3 and all(v[i] == v[i-1] + v[i-2] for i in range(2, len(v))):
            return v[-1] + v[-2]
        return v[-1] + d[-1]
    if "discounted by" in t:
        return n[0] * (1 - n[1] / 100)
    if "percentage change" in t:
        return (n[1] - n[0]) / n[0] * 100
    if "settlement period" in t:
        m = re.search(r"signed on (\d+ \w+ \d{4}) has a (\d+)-day", t)
        d0 = datetime.strptime(m.group(1), "%d %B %Y").date()
        return d0 + timedelta(days=int(m.group(2)))
    if "break even" in t:
        import math
        return round(n[0] / (n[1] - n[2]))
    if "ratio" in t and "split" in t:
        a, b = re.search(r"ratio (\d+):(\d+)", t).groups()
        a, b = float(a), float(b)
        share = a if "first" in t else b
        return n[0] * share / (a + b)
    if "overall average order value" in t:
        return (n[0]*n[1] + n[2]*n[3]) / (n[0] + n[2])
    if "converted to euros" in t:
        return n[0] * n[1]
    if "probability" in t:
        m = re.search(r"holds (.*?)\. If", t).group(1)
        parts = re.findall(r"(\d+) (\w+) tickets", m)
        total = sum(int(c) for c, _ in parts)
        target = re.search(r"it is an? (\w+) ticket", t).group(1)
        return sum(int(c) for c, k in parts if k == target) / total * 100
    if "total revenue" in t:
        return n[0] * n[1]
    return None

def pick(q, opts):
    v = compute(q["question_text"])
    if v is None:
        return None
    if isinstance(v, date):
        for L, o in opts.items():
            try:
                if datetime.strptime(o.strip(), "%d %B %Y").date() == v:
                    return L
            except ValueError:
                pass
        return None
    best, bd = None, None
    for L, o in opts.items():
        on = nums(o)
        if not on:
            continue
        d = abs(on[0] - v)
        if bd is None or d < bd:
            best, bd = L, d
    return best

def load(src):
    if src.startswith("http"):
        data = urllib.request.urlopen(src + "?t=" + str(datetime.now().timestamp())).read().decode()
    else:
        data = open(src).read()
    return list(csv.DictReader(io.StringIO(data)))

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else QURL
    rows = load(src)
    os.makedirs("answers", exist_ok=True)
    rounds = {}
    for r in rows:
        rounds.setdefault(int(r["round_id"]), []).append(r)
    unknown = 0
    for rid, qs in sorted(rounds.items()):
        path = f"answers/round-{rid:04d}.json"
        if os.path.exists(path):
            continue
        ans = {}
        for q in sorted(qs, key=lambda x: int(x["q_index"])):
            opts = {L: q[f"option_{L.lower()}"] for L in "ABCD"}
            try:
                a = pick(q, opts)
            except Exception:
                a = None
            if a is None:
                unknown += 1
                print(f"UNKNOWN r{rid} q{q['q_index']}: {q['question_text']}")
                a = "A"
            ans[f"q{q['q_index']}"] = a
        json.dump({"round_id": rid, "answers": ans}, open(path, "w"), indent=2)
        print("wrote", path)
    print("unknown:", unknown)

if __name__ == "__main__":
    main()
