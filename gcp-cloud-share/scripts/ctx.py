"""Print sentences matching a regex. Usage: python3 -I ctx.py <regex> <files...> [--max N]"""
import sys, re
args = sys.argv[1:]
mx = 5
if "--max" in args:
    i = args.index("--max"); mx = int(args[i+1]); del args[i:i+2]
pat = re.compile(args[0], re.I)
for f in args[1:]:
    t = open(f).read().replace("\n", " ")
    sents = re.split(r"(?<=[.;])\s+(?=[A-Z(•])", t)
    hits = [s.strip() for s in sents if pat.search(s)]
    print(f"== {f.split('/')[-1]} ({len(hits)})")
    for s in hits[:mx]:
        print("  -", s[:700])
