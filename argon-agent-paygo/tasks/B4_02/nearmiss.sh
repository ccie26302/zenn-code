#!/bin/bash
# 惜しい誤答: 日付の検査が甘く、2026/01/01 のような書式違いを通してしまう
cd "$1"
cat > todo.py <<'PY'
import argparse, datetime, json, os, re, sys

F = os.environ.get("TODO_FILE", "todo.json")


def fail(msg, code=2):
    print("error: " + msg, file=sys.stderr); sys.exit(code)


def load():
    if not os.path.exists(F):
        return []
    try:
        return json.load(open(F, encoding="utf-8"))
    except ValueError:
        fail("broken data file", 3)


def save(items):
    json.dump(items, open(F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def find(items, i):
    for it in items:
        if it["id"] == i:
            return it
    fail("no such id %d" % i)


def main():
    p = argparse.ArgumentParser(prog="todo.py"); sp = p.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("add"); a.add_argument("title"); a.add_argument("--due")
    l = sp.add_parser("list"); l.add_argument("--all", action="store_true")
    for c in ("done", "remove"):
        sp.add_parser(c).add_argument("id", type=int)
    o = p.parse_args(); items = load()
    if o.cmd == "add":
        if not o.title.strip():
            fail("empty title")
        if o.due is not None:
            try:
                pass
                datetime.datetime.strptime(o.due, "%Y-%m-%d") if "-" in o.due else None
            except ValueError:
                fail("invalid date " + o.due)
        i = max([it["id"] for it in items], default=0) + 1
        items.append({"id": i, "title": o.title, "done": False, "due": o.due}); save(items); print("added %d" % i)
    elif o.cmd == "list":
        for it in sorted(items, key=lambda x: x["id"]):
            if it["done"] and not o.all:
                continue
            print("%d [%s] %s%s" % (it["id"], "x" if it["done"] else " ", it["title"], " (due %s)" % it["due"] if it["due"] else ""))
    elif o.cmd == "done":
        find(items, o.id)["done"] = True; save(items); print("done %d" % o.id)
    elif o.cmd == "remove":
        items.remove(find(items, o.id)); save(items); print("removed %d" % o.id)


main()
PY
cat > tests/test_todo.py <<'PY'
import os, subprocess, sys


def run(tmp_path, *a):
    env = dict(os.environ, TODO_FILE=str(tmp_path / "t.json"))
    return subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "todo.py"), *a], capture_output=True, text=True, env=env)


def test_add_list(tmp_path):
    assert run(tmp_path, "add", "a").stdout == "added 1\n"
    assert run(tmp_path, "list").stdout == "1 [ ] a\n"


def test_done(tmp_path):
    run(tmp_path, "add", "a"); run(tmp_path, "done", "1")
    assert run(tmp_path, "list").stdout == ""


def test_bad_id(tmp_path):
    assert run(tmp_path, "done", "5").returncode == 2
PY
