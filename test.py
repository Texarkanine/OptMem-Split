#!/usr/bin/env python3
"""OptMem invariants, checked against a synthetic life of 5000 memories.

Uses a fake compressor (join + truncate) so the run is deterministic and free.
"""

import atexit
import contextlib
import datetime
import io
import ntpath
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from importlib.machinery import SourceFileLoader

# Isolate HOME and XDG_DATA_HOME before importing memo or running any
# command so test.py never reads or writes a real user or project store.
TEST_HOME = tempfile.mkdtemp(prefix="optmem-test-home-")
TEST_XDG = os.path.join(TEST_HOME, ".local", "share")
os.environ["HOME"] = TEST_HOME
os.environ["XDG_DATA_HOME"] = TEST_XDG
os.environ.pop("MEMORY_DIR", None)
atexit.register(shutil.rmtree, TEST_HOME, True)

HERE = os.path.dirname(os.path.realpath(__file__))
MEMO = os.path.join(HERE, "memo")
cli = SourceFileLoader("memo_cli", MEMO).load_module()
cover = cli.cover


def complete(T):
    """Every block buildable from T memories, smallest first. The oracle for
    the tool's `pending()`: written straight from the definition, so a bug in
    the fast version (which reads level lengths, never scanning) shows up."""
    out, size = [], 2
    while size <= T:
        out += [(i * size, (i + 1) * size) for i in range(T // size)]
        size *= 2
    return out

N = 2000
WAKE_LINES = cli.WAKE_LINES   # the shipped budget, not a second copy of it
PART_CHARS = cli.PART_CHARS
# Verified caps of the harnesses in the wild: Claude Code cuts a command's
# output at 30,000 chars (middle), pi at 50 KB / 2000 lines (head), Codex
# budgets 10,000 tokens. A part must fit the strictest of each kind.
CAP_CHARS, CAP_LINES = 30000, 2000
ok, fail = 0, 0


def check(cond, msg):
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print("FAIL: " + msg)


# ---- pure block math -------------------------------------------------

for T in list(range(1, 400)) + [1000, 4096, 10000, 65536, 100003]:
    c = cover(T, WAKE_LINES)
    check(len(c) <= WAKE_LINES, "T=%d: %d lines > budget" % (T, len(c)))
    check(c[0][0] == 0 and c[-1][1] == T, "T=%d: does not span [0,T)" % T)
    for a, b in zip(c, c[1:]):
        check(a[1] == b[0], "T=%d: gap or overlap at %s %s" % (T, a, b))
    for lo, hi in c:
        s = hi - lo
        check(s & (s - 1) == 0 and lo % s == 0,
              "T=%d: [%d,%d) is not an aligned power-of-two block" % (T, lo, hi))
    for a, b in zip(c, c[1:]):
        check(b[1] - b[0] <= a[1] - a[0],
              "T=%d: detail does not increase toward the present" % T)

check(cover(300, 320) == [(i, i + 1) for i in range(300)],
      "under budget, memory should be verbatim")

# every block a cover ever needs must be buildable. cover() costs a 60-step
# binary search, so this walks every tree shape up to 300 and then samples:
# the property is structural, not a function of the exact T.
seen = set()
for T in list(range(1, 300)) + [512, 700, 1000, 1023, 1024, 2000, 2999]:
    seen.update(b for b in cover(T, WAKE_LINES) if b[1] - b[0] > 1)
buildable = set(complete(3000))
check(seen <= buildable, "a cover wants a block that complete() never yields")

# work never spikes: naps created by one new memory
worst, prev = 0, 0
for T in range(1, N):
    cur = len(complete(T))
    worst = max(worst, cur - prev)
    prev = cur
check(worst <= 16, "a single memory created %d naps" % worst)

# ---- the real CLI ----------------------------------------------------

d = tempfile.mkdtemp(prefix="optmem-test-")
memo = [sys.executable, MEMO]


class Result:
    def __init__(self, returncode, stdout, stderr):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


SCOPED_CMDS = {"note", "nap", "recall", "zoom", "forget", "config", "import"}


def check_printed_commands(text):
    """Verify runtime command hints/orders printed by memo carry valid scope flags."""
    if not text or "## Memory" in text or "OptMem: a permanent" in text:
        return
    exe = cli.pretty(MEMO)
    for line in text.splitlines():
        m = re.search(
            r"(?:Run: |usage: |To create one, run: |Record the first with: |then run )(.+)$",
            line,
        )
        if not m:
            continue
        segment = m.group(1).strip()
        if segment.endswith(" again."):
            segment = segment[:-len(" again.")]
        elif segment.endswith("."):
            segment = segment[:-1]
        if "   #" in segment:
            segment = segment.split("   #", 1)[0].strip()
        try:
            tokens = shlex.split(segment)
        except ValueError:
            check(False, "unparseable printed command: %r" % line)
            continue
        if not tokens:
            continue
        check(tokens[0] == exe,
              "printed command did not name %r: %r" % (exe, line))
        rest = tokens[1:]
        has_here = "--here" in rest
        has_global = "--global" in rest
        pos = [t for t in rest if t not in ("--here", "--global")]
        if not pos:
            continue
        sub = pos[0]
        if sub in SCOPED_CMDS:
            check(has_here ^ has_global,
                  "printed %s command missing single scope flag: %r" % (sub, line))
        elif sub == "wake":
            check(not has_here,
                  "printed wake command must never carry --here: %r" % line)


def run(*args, store=None, scope="--global"):
    """One `memo` command, in-process via `cli.main(argv)`. Spawning an
    interpreter per call cost ~40ms x ~2000 naps; cross-process behaviour
    (locks, PATH, env) is tested with real processes below."""
    old_mem = os.environ.get("MEMORY_DIR")
    if store is False:
        os.environ.pop("MEMORY_DIR", None)
    else:
        os.environ["MEMORY_DIR"] = store or d
    argv = ([scope] if scope else []) + list(args)
    out, err, code = io.StringIO(), io.StringIO(), 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            cli.main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 0
    finally:
        if old_mem is None:
            os.environ.pop("MEMORY_DIR", None)
        else:
            os.environ["MEMORY_DIR"] = old_mem
    res = Result(code, out.getvalue(), err.getvalue())
    check_printed_commands(res.stdout)
    check_printed_commands(res.stderr)
    return res


def nap_id(out):
    """The block id from the command a nap prompt offers."""
    m = re.search(r"memo (?:--here|--global) nap (\d+)-(\d+)", out)
    return "%s-%s" % m.groups() if m else None


def offered(out):
    """The line offering a command. Every command handed to an agent must be
    an order, not a label: `Run: memo ...`, never `next: memo ...`."""
    return [l for l in out.splitlines()
            if re.search(r"memo (?:(?:--here|--global) nap |(?:--global )?wake )", l)]


# the real entry point still has to work: shebang, argv parsing, exit code
smoke = subprocess.run(memo + ["--global", "wake"], env=dict(os.environ, MEMORY_DIR=d),
                       capture_output=True, text=True)
check(smoke.returncode == 0 and "No memories yet" in smoke.stdout,
      "the memo CLI does not run: " + smoke.stdout + smoke.stderr)

# a typo in MEMORY_DIR must not silently open a second, empty identity
ghost = subprocess.run(memo + ["--global", "wake"], capture_output=True, text=True,
                       env=dict(os.environ, MEMORY_DIR=d + "-typo"))
check(ghost.returncode == 1 and "No memory at" in ghost.stderr,
      "a missing MEMORY_DIR was created instead of reported")
check(not os.path.exists(d + "-typo"), "a missing MEMORY_DIR was created")

# the fresh-user path: no MEMORY_DIR, wake works against a project memory it
# creates itself but says the global one is missing, init creates that one,
# prints the paste block, and is idempotent
fresh = {k: v for k, v in os.environ.items() if k != "MEMORY_DIR"}
fresh["HOME"] = tempfile.mkdtemp()
fresh["XDG_DATA_HOME"] = os.path.join(fresh["HOME"], ".local", "share")
noenv = subprocess.run(memo + ["wake"], capture_output=True, text=True, env=fresh)
check(noenv.returncode == 0 and "No global memory yet" in noenv.stdout
      and "memo init" in noenv.stdout,
      "with no global memory, wake must still work and point at init:\n"
      + noenv.stdout + noenv.stderr)
init = subprocess.run(memo + ["init"], capture_output=True, text=True, env=fresh)
check(init.returncode == 0 and "## Memory" in init.stdout
      and "You are a" in init.stdout, "init must print the AGENTS.md block")
check(os.path.exists(os.path.join(fresh["HOME"], ".optmem", "memory", "config")),
      "init must create ~/.optmem/memory with its config")
again = subprocess.run(memo + ["init"], capture_output=True, text=True, env=fresh)
check(again.returncode == 0 and "Found" in again.stdout, "init must be idempotent")
woke = subprocess.run(memo + ["wake"], capture_output=True, text=True, env=fresh)
check(woke.returncode == 0 and "You are awake." in woke.stdout,
      "after init, wake must work with zero configuration")

# Every command the tool prints must RUN on the machine it printed it on.
# `curl | sh` puts nothing on PATH, so a bare `memo nap ...` would not: the
# whole loop (note -> merge prompt -> nap) dies on `command not found`.
bare = dict(fresh, PATH="/usr/bin:/bin")
subprocess.run(memo + ["note", "--here", "the first thing that happened"], env=bare,
               capture_output=True)
asked = subprocess.run(memo + ["note", "--here", "the second thing that happened"],
                       env=bare, capture_output=True, text=True)
order = [l[5:] for l in asked.stdout.splitlines() if l.startswith("Run: ")]
check(len(order) == 1, "note did not order a compression: " + asked.stdout)
obeyed = subprocess.run(order[0].replace('"<your line>"', '"both things"'),
                        shell=True, env=bare, capture_output=True, text=True)
check(obeyed.returncode == 0 and "saved" in obeyed.stdout,
      "the order the tool printed does not run with nothing on PATH: %r -> %s"
      % (order[0], obeyed.stderr.strip()))

# a size written by hand into `config` must not brick the tool with a
# recovery that is itself broken: name the file and the line
badcfg = os.path.join(fresh["HOME"], ".optmem", "memory", "config")
with open(badcfg, "a") as f:
    f.write("WAKE_LNES = 100\n")
for c in (["wake"], ["--global", "config"]):
    r_ = subprocess.run(memo + c, capture_output=True, text=True, env=fresh)
    check(r_.returncode == 1 and "config line" in r_.stderr
          and "WAKE_LNES" in r_.stderr,
          "a typo in config does not say where it is: " + r_.stderr)
open(badcfg, "w").write("")

# the filesystem is the one thing the tool does not control: report it in the
# tool's own voice, never as a Python traceback
r_ = subprocess.run(memo + ["init"], capture_output=True, text=True,
                    env=dict(fresh, MEMORY_DIR=MEMO))   # a file, not a store
check(r_.returncode == 1 and "Traceback" not in r_.stderr
      and "Not a directory" in r_.stderr,
      "a filesystem error printed a traceback: " + r_.stderr)


r = run("note", "x" * 281)
check(r.returncode == 1 and "Too long" in r.stderr, "over-long note accepted")
r = run("note", "two\nlines")
check(r.returncode == 1 and "one line" in r.stderr, "multi-line note accepted")
r = run("note", "   ")
check(r.returncode == 1, "empty note accepted")
r = run("wake")
check("No memories yet" in r.stdout, "empty wake should say so")
check(r.stdout.rstrip().endswith("You are awake."),
      "an empty wake must still end with `You are awake.`")

# nap quotes #id text, not #id date text: a leading date in the quoted body
# is copied into summaries and then stacks. Wake still prints the date.
dn = tempfile.mkdtemp(prefix="optmem-nap-fmt-")
run("note", "alpha lasted", store=dn)
run("note", "beta lasted", store=dn)
r = run("nap", store=dn)
today = datetime.date.today().isoformat()
check("  #0 alpha lasted" in r.stdout,
      "nap source line must be #id text: " + r.stdout)
check("  #1 beta lasted" in r.stdout,
      "nap source line must be #id text: " + r.stdout)
check(("  #0 %s alpha lasted" % today) not in r.stdout,
      "nap source line must not include the log date: " + r.stdout)
check(not re.search(r"(?m)^  #\d+ \d{4}-\d{2}-\d{2} ", r.stdout),
      "nap source lines must not put YYYY-MM-DD after the id: " + r.stdout)
run("nap", nap_id(r.stdout), "alpha and beta lasted", store=dn)
w = run("wake", store=dn)
check(("#0 %s alpha lasted" % today) in w.stdout,
      "wake must still print the log date: " + w.stdout)
shutil.rmtree(dn)

with open(os.path.join(d, "seed.txt"), "w") as f:
    day = datetime.date(2020, 1, 1)
    for i in range(N):
        f.write("%s memory number %d, a thing that happened, was weighed "
                "against the rest of the week, turned out to matter more than "
                "anyone guessed at the time, and left a mark on every plan "
                "that followed it\n"
                % ((day + datetime.timedelta(days=i // 5)).isoformat(), i))
r = run("import", os.path.join(d, "seed.txt"))
check("Imported %d" % N in r.stdout, "import failed: " + r.stdout + r.stderr)
check(not os.path.exists(os.path.join(d, "config")),
      "a store wrote its own config file: the defaults are now frozen in it")

r = run("wake")
check(r.returncode == 1 and "Cannot wake" in r.stdout,
      "wake must refuse while work is pending")
check("wake again" in r.stdout,
      "the refusal must order the agent back to wake")
check("None" not in r.stdout, "the refusal printed a Python None")

# nap loop, with a fake compressor
naps = 0
r = run("nap")
check("Compress memories #" in r.stdout, "nap prompt must name its object")
while "Nothing left to compress" not in r.stdout:
    line = offered(r.stdout)
    check(bool(line), "no command offered:\n" + r.stdout + r.stderr)
    if not line:
        break
    check(line[0].startswith("Run: "), "a command was offered as a label, not "
          "an order: %r" % line[0])
    bid = nap_id(r.stdout)
    body = [l.strip() for l in r.stdout.splitlines() if l.startswith("  #")]
    r = run("nap", bid, (" ".join(body)[:280]).strip() or "empty")
    check(r.returncode == 0, "nap rejected a valid merge: " + r.stderr)
    naps += 1
check("You are awake" not in r.stdout,
      "nap must never claim the agent is awake; only wake may")
check(naps == len(complete(N)), "did %d naps, expected %d" % (naps, len(complete(N))))

r = run("wake")
check(r.returncode == 0, "wake still refuses after a full nap chain")

# the document survives pagination, and every part fits every harness's cap
parts, k = [], 1
while True:
    r = run("wake", str(k))
    if r.returncode != 0:
        break
    body = [l for l in r.stdout.splitlines() if l.startswith("#")]
    check(len(r.stdout) < CAP_CHARS, "part %d is %d chars, over the %d cap"
          % (k, len(r.stdout), CAP_CHARS))
    check(len(r.stdout.splitlines()) < CAP_LINES, "part %d is over %d lines"
          % (k, CAP_LINES))
    parts.append(body)
    k += 1
check(len(parts) > 1, "a %d-line memory should need more than one part" % WAKE_LINES)
lines = [l for p in parts for l in p]
check(len(lines) == WAKE_LINES, "woke with %d lines, want %d" % (len(lines), WAKE_LINES))
check(lines[-1].startswith("#%d " % (N - 1)), "newest memory not last / not raw")
check(lines[0].startswith("#0-"), "oldest line should be a summary block")
check(re.search(r"Run: \S*memo --global wake 2", run("wake").stdout),
      "part 1 must ORDER the next command, not label it")
check("You are awake." in run("wake", str(len(parts))).stdout,
      "last part must say it is last")
check(run("wake", str(len(parts) + 1)).returncode == 1, "a nonexistent part should fail")

# append-only: nothing was ever rewritten
logsz = os.path.getsize(os.path.join(d, "LOG.txt"))
run("note", "one more thing happened today")
check(os.path.getsize(os.path.join(d, "LOG.txt")) > logsz, "note did not append")
check(logsz % 320 == 0, "LOG.txt is not a whole number of records")
for f in os.listdir(os.path.join(d, "TREE")):
    check(os.path.getsize(os.path.join(d, "TREE", f)) % 288 == 0,
          "TREE/%s is not a whole number of records" % f)

# a nap when nothing is pending writes nothing and says so
r = run("nap", "0-1", "attempted overwrite")
check(r.returncode == 0 and "Nothing left to compress" in r.stdout,
      "nap with nothing pending must say so and write nothing")

# recall reaches memories the summaries lost, and matches the whole line:
# id and date included, not just the text
r = run("recall", "memory number 7,")
check(r.returncode == 0 and "#7 " in r.stdout, "recall missed a memory")
check("1 match." in r.stdout, "a single match is not `1 matches`: " + r.stdout)
r = run("recall", "^#7 ")
check("memory number 7," in r.stdout, "recall cannot find a memory by id")
r = run("recall", "2020-01-02")
check("#7 " in r.stdout and "5 matches." in r.stdout,
      "recall cannot find memories by date: " + r.stdout)


# zoom: one tree node, opened into its two halves. The tool only reads;
# the agent is the navigator: it descends from a wake line by halving, and
# may leap to any block id it can name.
def halves(bid):
    r = run("zoom", bid)
    check(r.returncode == 0, "zoom %s failed: %s" % (bid, r.stderr))
    out = []
    for line in r.stdout.splitlines():
        m = re.match(r"#(\d+)(?:-(\d+))? ", line)
        check(bool(m), "zoom printed a line with no id: %r" % line)
        a = int(m.group(1))
        out.append((a, int(m.group(2)) + 1 if m.group(2) else a + 1))
    return out


target, lo, hi, calls = 777, 0, 1024, 0
while hi - lo > 1:
    mid = (lo + hi) // 2
    kids = halves("%d-%d" % (lo, hi - 1))
    check(kids == [(lo, mid), (mid, hi)],
          "zoom %d-%d is not its two halves: %r" % (lo, hi - 1, kids))
    lo, hi = kids[target >= mid]
    calls += 1
check(lo == target and calls == 10,
      "halving 1024 memories took %d calls and landed on #%d" % (calls, lo))
check("memory number %d," % target in run("zoom", "776-777").stdout,
      "the last zoom must print the raw memories themselves")

# the unbuilt tail is named, the empty future is omitted
r = run("zoom", "1024-2047")  # T is N+1, so the right half has no summary
check("#1536-2047 not compressed yet" in r.stdout,
      "an unbuilt half must say so: " + r.stdout)
r = run("zoom", "%d-%d" % (N, N + 1))  # the newest memory + one not yet made
check(r.stdout.count("\n") == 1 and "#%d " % N in r.stdout,
      "a half beyond the newest memory must be omitted: " + r.stdout)

# zoom answers with the tree's own records, so the id must BE a node
check(run("zoom", "3-9").returncode == 1, "zoom accepted a non-block")
check(run("zoom", "9-3").returncode == 1, "zoom accepted a backwards range")
check(run("zoom").returncode == 1, "zoom with no id must show usage")
r = run("zoom", "1048576-2097151")
check(r.returncode == 1 and "beyond the memory" in r.stderr
      and "memo --global wake" in r.stderr, "zoom past the end must name a way back")


def treesize():
    t = os.path.join(d, "TREE")
    return sum(os.path.getsize(os.path.join(t, f)) for f in os.listdir(t))

before, logsize = treesize(), os.path.getsize(os.path.join(d, "LOG.txt"))
r = run("forget", "16-31")
check("16-31" in r.stdout, "forget did not report the block: " + r.stdout + r.stderr)
check(treesize() < before, "forget did not shrink the tree")
check(os.path.getsize(os.path.join(d, "LOG.txt")) == logsize, "forget touched the log")
check(run("wake").returncode == 1, "wake should refuse after a forget")
# a settled block cannot be rewritten. Resubmitting one (two sessions paid
# the same nap) is not an error: say it is settled, write nothing
mid = treesize()
r = run("nap", "0-1", "attempted overwrite")
check(r.returncode == 0 and "already settled" in r.stdout,
      "resubmitting a settled block was not reported as settled: " + r.stderr)
check(treesize() == mid, "resubmitting a settled block wrote something")
# a block that is neither settled nor next (here: a dropped ancestor,
# submitted before its half is rebuilt) is a real mistake
r = run("nap", "0-31", "out of order")
check(r.returncode == 1 and "Wrong block" in r.stderr,
      "an out-of-order block was accepted")
n = 0
while True:
    r = run("nap")
    if "Nothing left to compress" in r.stdout:
        break
    bid = nap_id(r.stdout)
    check(run("nap", bid, "rebuilt after forget").returncode == 0, "rebuild rejected")
    n += 1
check(n > 0, "forget created no work")
check(run("wake").returncode == 0, "wake still refuses after rebuilding")
check(treesize() == before, "tree did not return to its original size")
check(run("forget", "17-32").returncode == 1, "forgetting a non-block should fail")
# a summary that is not built yet is named as such, never left blank
run("forget", "16-31")
z = run("zoom", "0-31").stdout
check("#16-31 not compressed yet" in z, "zoom hid a missing summary: " + z)
while True:
    bid = nap_id(run("nap").stdout)
    if not bid:
        break
    run("nap", bid, "rebuilt after forget")
check(treesize() == before, "tree did not return to its original size")
check(run("forget", "1048576-1048577").returncode == 1, "forgetting a missing block should fail")

# UTF-8: multi-byte characters must not shift record boundaries or dodge limits
run("note", "reunião com João em São Paulo: ação aprovada, coração tranquilo")
run("note", "a plain ascii memory right after the accented one")
r = run("recall", "coração")
check("João" in r.stdout, "recall lost the accented memory: " + r.stdout + r.stderr)
r = run("recall", "plain ascii memory right after")
check("#%d " % (N + 2) in r.stdout, "record after a multi-byte one reads shifted")
r = run("note", "ã" * 150)
check(r.returncode == 1 and "300 bytes" in r.stderr,
      "multi-byte note dodged the byte limit: " + r.stderr)

# note landed -> its blocks are pending; settle before the final wake check
while True:
    r = run("nap")
    if "Nothing left to compress" in r.stdout:
        break
    bid = nap_id(r.stdout)
    run("nap", bid, "settled")
check(run("wake").returncode == 0, "wake refuses at the very end")

# a part is rendered as of T, so a note landing mid-wake cannot shift a
# boundary and silently drop a line
T0 = os.path.getsize(os.path.join(d, "LOG.txt")) // 320
before = run("wake", "1", str(T0))
check(before.returncode == 0, "as-of-T wake failed: " + before.stdout + before.stderr)
run("note", "a note that lands between two wake calls")
check(run("wake", "1", str(T0)).stdout == before.stdout,
      "a note between parts changed an already-rendered part")
check(run("wake", "1", str(T0 + 99)).returncode == 1, "wake accepted a future T")

# ...and the agent pays that note's compressions on the spot, as it is told
# to. The tree then holds MORE blocks than the snapshot needs: a level must
# never count as negative work, or the rest of the wake is refused with an
# impossible number.
while True:
    r = run("nap")
    if "Nothing left to compress" in r.stdout:
        break
    run("nap", nap_id(r.stdout), "settled mid-wake")
r = run("wake", "1", str(T0))
check(r.returncode == 0 and r.stdout == before.stdout,
      "a compression paid mid-wake broke the rest of the wake:\n"
      + r.stdout + r.stderr)
for T in list(range(1, 40)) + [T0 - 1, T0, T0 + 1]:
    check(cli.pending_count(d, T) == len(cli.pending(d, T)),
          "pending_count disagrees with pending at T=%d" % T)

# recall must not hand back more than a harness will carry
r = run("recall", "memory number")
check(len(r.stdout) < CAP_CHARS, "recall returned %d chars" % len(r.stdout))
check("Narrow the regex" in r.stdout, "recall did not say it had been capped")

# ---- concurrency and crash recovery ----------------------------------

d2 = tempfile.mkdtemp(prefix="optmem-race-")
env2 = dict(os.environ, MEMORY_DIR=d2)
P = 16  # real processes: this is the cross-process lock under test
procs = [subprocess.Popen(memo + ["--global", "note", "parallel note %d" % i], env=env2,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
         for i in range(P)]
for p in procs:
    p.wait()
with open(os.path.join(d2, "LOG.txt"), "rb") as f:
    recs = [f.read(320) for _ in range(P)]
ids = [r.decode().split()[0] for r in recs if r.strip()]
check(len(ids) == P, "%d of %d parallel notes survived" % (len(ids), P))
check(len(set(ids)) == P, "parallel notes collided on an id: %s" % sorted(ids))
check(sorted(ids) == sorted("#%d" % i for i in range(P)),
      "parallel note ids are not 0..%d: %s" % (P - 1, sorted(ids)))

# a crash mid-append leaves a partial record; the next append must drop it,
# or every later record is misaligned forever
with open(os.path.join(d2, "LOG.txt"), "ab") as f:
    f.write(b"#99 2026-01-01 a half-written record killed by a power cut")
r = run("note", "the memory right after a torn write", store=d2)
check(r.returncode == 0, "note failed after a torn write: " + r.stderr)
sz = os.path.getsize(os.path.join(d2, "LOG.txt"))
check(sz % 320 == 0, "LOG.txt left misaligned after a torn write: %d" % sz)
check("Saved as #%d" % P in r.stdout, "torn record was counted as a memory")
r = run("recall", "right after a torn write", store=d2)
check("#%d " % P in r.stdout, "the memory after a torn write reads wrong")

# a memory small enough to fit one part must still end with the terminator
# the agent was told to wait for
while True:
    r = run("nap", store=d2)
    if "Nothing left to compress" in r.stdout:
        break
    bid = nap_id(r.stdout)
    run("nap", bid, "settled", store=d2)
r = run("wake", store=d2)
check(r.stdout.rstrip().endswith("You are awake."),
      "a one-part wake never says `You are awake.`:\n" + r.stdout)

# a blank summary record (a corrupt write) is work nap cannot see: wake must
# name the one exit, `forget`, instead of refusing forever
d3 = tempfile.mkdtemp(prefix="optmem-blank-")
for i in range(4):
    run("note", "corrupt store memory %d" % i, store=d3)
for bid, s in (("0-1", "one"), ("2-3", "two"), ("0-3", "all")):
    run("nap", bid, s, store=d3)
with open(os.path.join(d3, "config"), "w") as f:
    f.write("WAKE_LINES = 2\n")
with open(os.path.join(d3, "TREE", "2"), "r+b") as f:
    f.write(b" " * 287 + b"\n")
r = run("wake", store=d3)
check(r.returncode == 1 and "forget 0-1" in r.stderr
      and "None" not in r.stdout,
      "a blank summary must point at forget:\n" + r.stdout + r.stderr)

# an unreadable level is a filesystem failure and must surface as one --
# reading it as "not compressed yet" offers work that cannot be done
os.chmod(os.path.join(d3, "TREE", "2"), 0)
r_ = subprocess.run(memo + ["--global", "wake"], capture_output=True, text=True,
                    env=dict(os.environ, MEMORY_DIR=d3))
check(r_.returncode == 1 and "Permission denied" in r_.stderr
      and "not compressed" not in r_.stdout,
      "an unreadable level was read as pending work: " + r_.stdout + r_.stderr)
os.chmod(os.path.join(d3, "TREE", "2"), 0o644)

# an impossible calendar date would poison every later import: the store's
# order check compares against it forever
with open(os.path.join(d3, "bad.txt"), "w") as f:
    f.write("2027-99-99 an impossible date\n")
r = run("import", os.path.join(d3, "bad.txt"), store=d3)
check(r.returncode == 1 and "not a real date" in r.stderr,
      "import accepted an impossible date: " + r.stdout + r.stderr)
shutil.rmtree(d3)

# the same blank-record dead end at the other site: a big block's half
d4 = tempfile.mkdtemp(prefix="optmem-half-")
for i in range(32):
    run("note", "half probe memory %d" % i, store=d4)
while True:
    r = run("nap", store=d4)
    if "Compress memories #0-31 " in r.stdout:
        break
    run("nap", nap_id(r.stdout), "settled", store=d4)
with open(os.path.join(d4, "TREE", "16"), "r+b") as f:
    f.write(b" " * 287 + b"\n")
r = run("nap", store=d4)
check(r.returncode == 1 and "forget 0-15" in r.stderr,
      "a blank half summary must point at forget: " + r.stdout + r.stderr)
shutil.rmtree(d4)

# the store is UTF-8 whatever the locale says: without pinning the streams,
# one arrow in a memory made wake crash forever on a latin-1 machine
d5 = tempfile.mkdtemp(prefix="optmem-utf8-")
run("note", "an arrow \u2192 survives any locale", store=d5)
r_ = subprocess.run(memo + ["--global", "wake"], capture_output=True,
                    env=dict(os.environ, MEMORY_DIR=d5,
                             PYTHONIOENCODING="latin-1"))
check(r_.returncode == 0 and "\u2192".encode() in r_.stdout,
      "wake must print UTF-8 on a non-UTF-8 locale: "
      + repr(r_.stdout + r_.stderr))

# an import file that is not UTF-8 is refused -- neither a traceback nor,
# worse, silently mis-decoded into mojibake and stored forever
with open(os.path.join(d5, "latin1.txt"), "wb") as f:
    f.write(b"2027-01-01 caf\xe9 in latin-1\n")
r = run("import", os.path.join(d5, "latin1.txt"), store=d5)
check(r.returncode == 1 and "not UTF-8" in r.stderr,
      "a non-UTF-8 import file must be refused: " + r.stdout + r.stderr)

# a summary record holding invalid UTF-8 is the blank-record dead end in
# another coat: it must name forget, not print a traceback
run("note", "utf8 probe second memory", store=d5)
run("nap", "0-1", "both utf8 probes", store=d5)
with open(os.path.join(d5, "TREE", "2"), "r+b") as f:
    f.write(b"\xff\xfe corrupt bytes")
r = run("zoom", "0-3", store=d5)
check(r.returncode == 1 and "forget 0-1" in r.stderr,
      "a corrupt summary must point at forget: " + r.stdout + r.stderr)
shutil.rmtree(d5)

# re-running init on a lived-in store must not touch one byte of it: the
# whole setup is idempotent, so it is safe on every provision. `init` only
# ever makedirs(exist_ok), opens LOG.txt for APPEND, and writes `config`
# when absent -- never truncating, never overwriting a tuned config.
def fingerprint(path):
    out = {}
    for root, _, files in os.walk(path):
        for f in files:
            if f == ".lock":
                continue
            p = os.path.join(root, f)
            out[os.path.relpath(p, path)] = open(p, "rb").read()
    return out


# `memo config` is how a size is changed: it writes the file the tool reads
# back, an empty value restores the default, and a wake obeys immediately --
# nothing is recomputed, because a size only selects what gets printed.
r = run("config", "WAKE_LINES=12")
check("12" in r.stdout and "default 96" in r.stdout, "config did not set:\n" + r.stdout)
check(len(run("wake").stdout.splitlines()) <= 13, "wake ignored the new size")
r = run("config", "WAKE_LINES=")
check("default" not in r.stdout, "an empty value did not restore the default")
check(len(run("wake").stdout.splitlines()) > 13, "the default did not come back")
for bad in ("WAKE_LINES=0", "WAKE_LINES=x", "ENTRY_CHARS=999", "NOPE=1", "WAKE_LINES"):
    check(run("config", bad).returncode == 1, "config accepted %s" % bad)

with open(os.path.join(d, "config"), "a") as f:
    f.write("WAKE_LINES=12\n")           # a size the user tuned by hand
before = fingerprint(d)
check(len(before) > 3 and before["LOG.txt"], "the store under test is empty")
for _ in range(3):
    r = run("init")
    check(r.returncode == 0 and "Found" in r.stdout, "init on a live store failed")
check(fingerprint(d) == before, "init modified an existing memory")
r = run("wake")
check(r.stdout.rstrip().endswith("You are awake."), "wake broke after re-init")

# ---- scope: project slug resolution and checkout routing
# Every synthetic-life test above pins MEMORY_DIR with --global.
xdg = tempfile.mkdtemp(prefix="optmem-xdg-")
os.environ["XDG_DATA_HOME"] = xdg
os.environ.pop("MEMORY_DIR", None)
real_git = cli.git


def as_repo(url):
    """Resolve a scope as if `git remote get-url origin` printed `url`, or as
    if there were no remote (None) and no checkout either."""
    cli.git = lambda *a: url if a[:2] == ("remote", "get-url") and url else ""
    try:
        return cli.scope_dir()
    finally:
        cli.git = real_git


ssh = as_repo("git@github-texarkanine.com:Texarkanine/OptMem-Split.git")
check(ssh == os.path.join(xdg, "optmem", "repo", "Texarkanine", "OptMem-Split"),
      "an ssh remote did not reduce to owner/repo: " + ssh)
check(as_repo("https://github.com/Texarkanine/OptMem-Split") == ssh,
      "one repo split across two remote spellings")
check(as_repo("git@github.com:Texarkanine/OptMem-Split.git/") == ssh,
      "a trailing slash forked the memory of one repo")
check(as_repo(None).startswith(os.path.join(xdg, "optmem", "path")),
      "no remote did not fall back to the path")
check(as_repo("") == as_repo(None), "an empty remote is not the no-remote case")

# Windows strings, proven on POSIX via ntpath: no Windows runner.
win_dir = r"C:\Users\Austin\git\foo"
check(cli.path_slug(win_dir, path=ntpath)
      == ntpath.join("path", "c", "users", "austin", "git", "foo"),
      "a Windows cwd did not nest under path/: "
      + cli.path_slug(win_dir, path=ntpath))
check(cli.path_slug(r"C:/Users/Austin/git/foo", path=ntpath)
      == cli.path_slug(win_dir, path=ntpath),
      "C:/ vs C:\\ forked the path-local memory")
check(cli.path_slug(r"S:\Users\Austin\git\foo", path=ntpath)
      == ntpath.join("path", "s", "users", "austin", "git", "foo"),
      "a subst drive did not nest under path/")
check(":" not in cli.path_slug(win_dir, path=ntpath),
      "a colon survived in the path-local slug")
posix_here = os.path.normcase(os.path.abspath("/tmp/optmem-scope-posix"))
check(cli.path_slug(posix_here) == os.path.join("path", *posix_here.strip(os.sep).split(os.sep)),
      "POSIX path-local slug changed: " + cli.path_slug(posix_here))

# One directory, one path-local memory, however the path was spelled.
# link → mid → the directory, and a link that is not the last component.
link_base = tempfile.mkdtemp(prefix="optmem-link-")
real_dir = os.path.join(link_base, "optmem-real-dir")
os.mkdir(real_dir)
mid = os.path.join(link_base, "optmem-mid-link")
outer = os.path.join(link_base, "optmem-outer-link")
os.symlink("optmem-real-dir", mid)
os.symlink("optmem-mid-link", outer)
os.mkdir(os.path.join(real_dir, "leaf"))
check(cli.path_slug(outer) == cli.path_slug(real_dir),
      "a symlink chain forked the path-local memory: " + cli.path_slug(outer))
check(cli.path_slug(os.path.join(mid, "leaf"))
      == cli.path_slug(os.path.join(real_dir, "leaf")),
      "a link in the middle of the path forked the memory: "
      + cli.path_slug(os.path.join(mid, "leaf")))
check("optmem-outer-link" not in cli.path_slug(outer).split(os.sep)
      and "optmem-mid-link" not in cli.path_slug(outer).split(os.sep),
      "a symlink chain slugged to the link name: " + cli.path_slug(outer))
shutil.rmtree(link_base)


class _JunctionPaths:
    """ntpath, except realpath follows one junction. Off Windows, ntpath.realpath
    is abspath, so a junction cannot be shown with a real path string."""

    sep = ntpath.sep
    normcase = staticmethod(ntpath.normcase)
    abspath = staticmethod(ntpath.abspath)
    splitdrive = staticmethod(ntpath.splitdrive)
    join = staticmethod(ntpath.join)

    @staticmethod
    def realpath(p):
        return ntpath.abspath(p).replace(r"\via-junction\proj", r"\real-dir\proj")


junction = r"C:\work\via-junction\proj"
junction_target = r"C:\work\real-dir\proj"
check(cli.path_slug(junction, path=_JunctionPaths)
      == cli.path_slug(junction_target, path=_JunctionPaths),
      "a Windows junction forked the path-local memory: "
      + cli.path_slug(junction, path=_JunctionPaths))

win_origin = r"C:\Users\Austin\src\widget.git"
check(cli.repo_slug(win_origin, path=ntpath)
      == ntpath.join("repo", "src", "widget"),
      "a Windows-path origin did not reduce to owner/repo: "
      + cli.repo_slug(win_origin, path=ntpath))
rooted = ntpath.join(r"C:\data\optmem", cli.repo_slug(win_origin, path=ntpath))
check(rooted.startswith(r"C:\data\optmem" + ntpath.sep),
      "a Windows-path origin threw the store out of optmem: " + rooted)
check(as_repo(win_origin).startswith(os.path.join(xdg, "optmem", "repo")),
      "a Windows-path origin left optmem: " + as_repo(win_origin))
check("\\" not in as_repo(win_origin) and ":" not in as_repo(win_origin)[len(xdg):],
      "a Windows-path origin kept a drive or backslash in the slug: "
      + as_repo(win_origin))

# end to end: a real checkout remembers into its own memory, not the global.
repo = tempfile.mkdtemp(prefix="optmem-repo-")
subprocess.run(["git", "init", "-q", repo], check=True)
subprocess.run(["git", "-C", repo, "remote", "add", "origin",
                "git@github.com:acme/widget.git"], check=True)
e2e = subprocess.run(memo + ["note", "--here", "scoped memories land in the project"],
                     cwd=repo, capture_output=True, text=True,
                     env=dict(os.environ, XDG_DATA_HOME=xdg))
check(e2e.returncode == 0 and "Saved as #0." in e2e.stdout,
      "a fresh checkout could not record its first memory: "
      + e2e.stdout + e2e.stderr)
log = os.path.join(xdg, "optmem", "repo", "acme", "widget", "LOG.txt")
check(os.path.exists(log), "the project memory was not created at " + log)
r = subprocess.run(memo + ["recall", "--here", "scoped"], cwd=repo, capture_output=True,
                   text=True, env=dict(os.environ, XDG_DATA_HOME=xdg))
check("1 match" in r.stdout or "scoped memories" in r.stdout,
      "recall did not read the project memory: " + r.stdout + r.stderr)

shutil.rmtree(repo)
shutil.rmtree(xdg)
os.environ["XDG_DATA_HOME"] = TEST_XDG
shutil.rmtree(d2)
shutil.rmtree(d)


def sub(args, env, cwd=None):
    """Run memo as a subprocess and verify any printed command hints/orders."""
    r = subprocess.run(memo + list(args), cwd=cwd, env=env,
                       capture_output=True, text=True)
    check_printed_commands(r.stdout)
    check_printed_commands(r.stderr)
    return r


def active_config(store_dir):
    """Parse active (uncommented) NAME = VALUE settings from a store's config."""
    out = {}
    for line in open(os.path.join(store_dir, "config"), encoding="utf-8"):
        body = line.split("#", 1)[0].strip()
        if "=" in body:
            k, v = body.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# ---- scope flags and token parsing ----


def test_scope_flag_policy():
    """note, nap, recall, zoom, forget, config, and import each require
    exactly one of --here or --global anywhere in argv; missing or both exits 1
    with distinct diagnostics on stderr, leaves LOG.txt unchanged, and creates
    no store in a fresh project; each scoped command mutates only the named store."""
    base = tempfile.mkdtemp(prefix="optmem-scope-flags-")
    try:
        xdg_dir = os.path.join(base, "xdg")
        g_dir = os.path.join(base, "global")
        repo_dir = os.path.join(base, "repo")
        seed = os.path.join(base, "seed.txt")
        os.makedirs(repo_dir)
        subprocess.run(["git", "init", "-q", repo_dir], check=True)
        subprocess.run(["git", "-C", repo_dir, "remote", "add", "origin",
                        "git@github.com:scope/proj.git"], check=True)
        with open(seed, "w") as f:
            f.write("2026-01-01 seeded memory\n")
        env = dict(os.environ, HOME=base, XDG_DATA_HOME=xdg_dir, MEMORY_DIR=g_dir)
        r = sub(["init"], env, cwd=repo_dir)
        check(r.returncode == 0, "scope setup init failed: " + r.stderr)
        g_before = fingerprint(g_dir)
        proj_store = os.path.join(xdg_dir, "optmem", "repo", "scope", "proj")

        cases = [
            ["note", "x"],
            ["nap"],
            ["recall", "x"],
            ["zoom", "0-1"],
            ["forget", "0-1"],
            ["config"],
            ["import", seed],
        ]
        for args in cases:
            r_none = sub(args, env, cwd=repo_dir)
            check(r_none.returncode == 1 and not r_none.stdout
                  and "Scope is required" in r_none.stderr
                  and "--here" in r_none.stderr and "--global" in r_none.stderr,
                  "missing scope on %r should report Scope is required: %r / %r"
                  % (args, r_none.stdout, r_none.stderr))
            r_both = sub(["--here", "--global"] + args, env, cwd=repo_dir)
            check(r_both.returncode == 1 and not r_both.stdout
                  and "Choose one scope, not both" in r_both.stderr
                  and "--here" in r_both.stderr and "--global" in r_both.stderr,
                  "both scopes on %r should report Choose one scope, not both: %r / %r"
                  % (args, r_both.stdout, r_both.stderr))
            check(not os.path.exists(proj_store),
                  "failed scope check on %r created project store" % (args,))
            check(fingerprint(g_dir) == g_before,
                  "failed scope check on %r modified global store" % (args,))

        # Flag placement anywhere in argv (before, middle, end) for --here and --global
        check(sub(["--here", "note", "proj zero"], env, cwd=repo_dir).returncode == 0,
              "--here before note failed")
        check(sub(["note", "--here", "proj one"], env, cwd=repo_dir).returncode == 0,
              "--here after note failed")
        check(sub(["note", "proj two", "--here"], env, cwd=repo_dir).returncode == 0,
              "--here at end of note failed")
        check(sub(["--global", "note", "glob zero"], env, cwd=repo_dir).returncode == 0,
              "--global before note failed")
        check(sub(["note", "--global", "glob one"], env, cwd=repo_dir).returncode == 0,
              "--global after note failed")
        check(sub(["note", "glob two", "--global"], env, cwd=repo_dir).returncode == 0,
              "--global at end of note failed")

        # Missing/both scope on live stores leaves LOG.txt unchanged
        p_log = os.path.join(proj_store, "LOG.txt")
        p_before = open(p_log, "rb").read()
        g_log = os.path.join(g_dir, "LOG.txt")
        g_log_before = open(g_log, "rb").read()
        check(sub(["note", "must not write"], env, cwd=repo_dir).returncode == 1,
              "unscoped note on live store accepted")
        check(sub(["note", "--here", "--global", "must not write"], env, cwd=repo_dir).returncode == 1,
              "dual-scoped note on live store accepted")
        check(open(p_log, "rb").read() == p_before, "unscoped/dual note altered project LOG.txt")
        check(open(g_log, "rb").read() == g_log_before, "unscoped/dual note altered global LOG.txt")

        # recall, nap, zoom, forget, config, import each hit only the named store
        rh = sub(["recall", "--here", "proj zero"], env, cwd=repo_dir)
        check(rh.returncode == 0 and "proj zero" in rh.stdout,
              "recall --here missed project note: " + rh.stdout + rh.stderr)
        check("No match." in sub(["recall", "--here", "glob zero"], env, cwd=repo_dir).stdout,
              "recall --here leaked global note")
        rg = sub(["recall", "--global", "glob zero"], env, cwd=repo_dir)
        check(rg.returncode == 0 and "glob zero" in rg.stdout,
              "recall --global missed global note: " + rg.stdout + rg.stderr)
        check("No match." in sub(["recall", "--global", "proj zero"], env, cwd=repo_dir).stdout,
              "recall --global leaked project note")

        p_tree2 = os.path.join(proj_store, "TREE", "2")
        g_tree2 = os.path.join(g_dir, "TREE", "2")
        check(sub(["nap", "--here", "0-1", "proj pair"], env, cwd=repo_dir).returncode == 0,
              "nap --here failed")
        check(os.path.exists(p_tree2) and "proj pair" in open(p_tree2, encoding="utf-8").read(),
              "nap --here did not write project TREE/2")
        check(not os.path.exists(g_tree2),
              "nap --here unexpectedly created global TREE/2")
        check(sub(["nap", "0-1", "glob pair", "--global"], env, cwd=repo_dir).returncode == 0,
              "nap --global at end failed")
        check(os.path.exists(g_tree2) and "glob pair" in open(g_tree2, encoding="utf-8").read(),
              "nap --global did not write global TREE/2")
        check("proj pair" in open(p_tree2, encoding="utf-8").read()
              and "glob pair" not in open(p_tree2, encoding="utf-8").read(),
              "nap --global modified project TREE/2")

        zh = sub(["zoom", "--here", "0-1"], env, cwd=repo_dir)
        check(zh.returncode == 0 and "proj zero" in zh.stdout and "glob zero" not in zh.stdout,
              "zoom --here wrong content: " + zh.stdout + zh.stderr)
        zg = sub(["zoom", "0-1", "--global"], env, cwd=repo_dir)
        check(zg.returncode == 0 and "glob zero" in zg.stdout and "proj zero" not in zg.stdout,
              "zoom --global wrong content: " + zg.stdout + zg.stderr)

        check(sub(["forget", "--here", "0-1"], env, cwd=repo_dir).returncode == 0,
              "forget --here failed")
        check(os.path.getsize(p_tree2) == 0,
              "forget --here did not drop project TREE/2 summary")
        check("glob pair" in open(g_tree2, encoding="utf-8").read(),
              "forget --here modified global TREE/2")
        check(sub(["forget", "--global", "0-1"], env, cwd=repo_dir).returncode == 0,
              "forget --global failed")
        check(os.path.getsize(g_tree2) == 0,
              "forget --global did not drop global TREE/2 summary")

        check(sub(["config", "--here", "WAKE_LINES=40"], env, cwd=repo_dir).returncode == 0,
              "config --here failed")
        check(active_config(proj_store).get("WAKE_LINES") == "40",
              "config --here did not persist active WAKE_LINES=40 in project config")
        check("WAKE_LINES" not in active_config(g_dir),
              "config --here leaked WAKE_LINES override into global config")
        check(re.search(r"^WAKE_LINES\s+40\b",
                        sub(["config", "--here"], env, cwd=repo_dir).stdout, re.M),
              "config --here stdout did not report WAKE_LINES 40")
        check(re.search(r"^WAKE_LINES\s+%d\b" % WAKE_LINES,
                        sub(["config", "--global"], env, cwd=repo_dir).stdout, re.M),
              "config --global stdout did not keep default WAKE_LINES")
        check(sub(["config", "--global", "WAKE_LINES=50"], env, cwd=repo_dir).returncode == 0,
              "config --global failed")
        check(active_config(g_dir).get("WAKE_LINES") == "50",
              "config --global did not persist active WAKE_LINES=50 in global config")
        check(active_config(proj_store).get("WAKE_LINES") == "40",
              "config --global altered project WAKE_LINES")
        check(re.search(r"^WAKE_LINES\s+50\b",
                        sub(["config", "--global"], env, cwd=repo_dir).stdout, re.M),
              "config --global stdout did not report WAKE_LINES 50")

        # Future-dated import after today's notes
        fut = os.path.join(base, "future.txt")
        with open(fut, "w") as f:
            f.write("2099-01-01 imported future note\n")
        check(sub(["import", "--here", fut], env, cwd=repo_dir).returncode == 0,
              "import --here failed")
        check("imported future note" in sub(["recall", "--here", "imported future"], env, cwd=repo_dir).stdout,
              "import --here did not land in project store")
        check("No match." in sub(["recall", "--global", "imported future"], env, cwd=repo_dir).stdout,
              "import --here leaked into global store")
        check(sub(["import", fut, "--global"], env, cwd=repo_dir).returncode == 0,
              "import --global failed")
        check("imported future note" in sub(["recall", "--global", "imported future"], env, cwd=repo_dir).stdout,
              "import --global did not land in global store")
    finally:
        shutil.rmtree(base)


def test_exact_flag_tokens():
    """Only exact --here, --global, -h, and --help tokens are parsed as flags;
    similar tokens (--helpiferous, -help, --hereish, --globally) and positional
    `help` are recorded verbatim as memory data."""
    base = tempfile.mkdtemp(prefix="optmem-flag-tokens-")
    try:
        xdg_dir = os.path.join(base, "xdg")
        repo_dir = os.path.join(base, "repo")
        os.makedirs(repo_dir)
        subprocess.run(["git", "init", "-q", repo_dir], check=True)
        subprocess.run(["git", "-C", repo_dir, "remote", "add", "origin",
                        "git@github.com:demo/tokens.git"], check=True)
        env = dict(os.environ, HOME=base, XDG_DATA_HOME=xdg_dir)
        env.pop("MEMORY_DIR", None)

        tokens = ["--helpiferous", "-help", "--hereish", "--globally", "help"]
        for i, tok in enumerate(tokens):
            r = sub(["note", "--here", tok], env, cwd=repo_dir)
            check(r.returncode == 0 and ("Saved as #%d." % i) in r.stdout,
                  "literal token %r was not saved: rc=%d out=%r err=%r"
                  % (tok, r.returncode, r.stdout, r.stderr))
        rec = sub(["recall", "--here", "--helpiferous"], env, cwd=repo_dir)
        check(rec.returncode == 0 and "#0 " in rec.stdout and "--helpiferous" in rec.stdout,
              "--helpiferous was not recalled: " + rec.stdout + rec.stderr)
        rec_all = sub(["recall", "--here", "help"], env, cwd=repo_dir)
        check("#0 " in rec_all.stdout and "#1 " in rec_all.stdout and "#4 " in rec_all.stdout,
              "literal help-like tokens missing from recall: " + rec_all.stdout)
    finally:
        shutil.rmtree(base)


# ---- store routing: MEMORY_DIR, XDG_DATA_HOME, and default global ----


def test_store_routing():
    """Verify store routing and state isolation across global and project stores:
    - With MEMORY_DIR unset, --global uses ~/.optmem/memory and --here uses XDG_DATA_HOME.
    - With MEMORY_DIR set, MEMORY_DIR moves only the global store while --here stays on XDG_DATA_HOME.
    - Missing MEMORY_DIR fails --global without creating it, while --here creates the project store.
    - init accepts/ignores scope flags, creates the global store, and writes a --global config hint.
    - Bare wake reads global then project without leaking global knob overrides into project wake;
      wake --global reads only the global store.
    - Repeated in-process cli.main(argv) calls reset command scope, tool prefix, and knob defaults internally."""
    base = tempfile.mkdtemp(prefix="optmem-store-routing-")
    try:
        xdg_dir = os.path.join(base, "xdg")
        missing_g = os.path.join(base, "missing-global")
        repo1 = os.path.join(base, "repo1")
        repo2 = os.path.join(base, "repo2")
        for rdir, origin in ((repo1, "git@github.com:demo/one.git"),
                             (repo2, "git@github.com:demo/two.git")):
            os.makedirs(rdir)
            subprocess.run(["git", "init", "-q", rdir], check=True)
            subprocess.run(["git", "-C", rdir, "remote", "add", "origin", origin], check=True)

        # Unset MEMORY_DIR routes --global to $HOME/.optmem/memory and --here to $XDG_DATA_HOME
        default_home = os.path.join(base, "default-home")
        default_xdg = os.path.join(base, "default-xdg")
        os.makedirs(default_home)
        env_default = dict(os.environ, HOME=default_home, XDG_DATA_HOME=default_xdg)
        env_default.pop("MEMORY_DIR", None)
        default_g = os.path.join(default_home, ".optmem", "memory")
        check(sub(["init"], env_default, cwd=repo1).returncode == 0,
              "default-home init failed")
        check(os.path.isdir(default_g) and not os.path.exists(default_xdg),
              "init with unset MEMORY_DIR did not create ~/.optmem/memory exclusively")
        check(sub(["note", "--global", "default global memory"], env_default, cwd=repo1).returncode == 0,
              "note --global with unset MEMORY_DIR failed")
        check("default global memory" in open(os.path.join(default_g, "LOG.txt")).read(),
              "note --global with unset MEMORY_DIR missed ~/.optmem/memory")
        check(sub(["note", "--here", "default xdg project memory"], env_default, cwd=repo1).returncode == 0,
              "note --here with unset MEMORY_DIR failed")
        p1_default_log = os.path.join(default_xdg, "optmem", "repo", "demo", "one", "LOG.txt")
        check("default xdg project memory" in open(p1_default_log).read()
              and "default xdg project memory" not in open(os.path.join(default_g, "LOG.txt")).read(),
              "note --here with unset MEMORY_DIR did not isolate into XDG_DATA_HOME")

        env = dict(os.environ, HOME=base, XDG_DATA_HOME=xdg_dir, MEMORY_DIR=missing_g)

        # Missing MEMORY_DIR makes --global commands fail and create nothing
        for args in (["wake", "--global"], ["note", "--global", "nope"], ["recall", "--global", "x"]):
            r = sub(args, env, cwd=repo1)
            check(r.returncode == 1 and "No memory at" in r.stderr
                  and "--global init" in r.stderr,
                  "missing MEMORY_DIR on %r did not fail properly: %r" % (args, r.stderr))
            check(not os.path.exists(missing_g),
                  "missing MEMORY_DIR was created by %r" % (args,))

        # Bare wake with missing MEMORY_DIR says no global memory, does not create it, wakes project
        bw = sub(["wake"], env, cwd=repo1)
        check(bw.returncode == 0 and "No global memory yet" in bw.stdout
              and "You are awake." in bw.stdout,
              "bare wake with missing MEMORY_DIR failed: " + bw.stdout + bw.stderr)
        check(not os.path.exists(missing_g), "bare wake created missing MEMORY_DIR")

        # --here in a fresh repo creates project store under XDG_DATA_HOME even when MEMORY_DIR is missing
        nh = sub(["note", "--here", "created despite missing MEMORY_DIR"], env, cwd=repo2)
        check(nh.returncode == 0 and "Saved as #0." in nh.stdout,
              "--here failed when MEMORY_DIR was missing: " + nh.stdout + nh.stderr)
        check(not os.path.exists(missing_g), "--here created missing MEMORY_DIR")
        p2_log = os.path.join(xdg_dir, "optmem", "repo", "demo", "two", "LOG.txt")
        check(os.path.exists(p2_log), "--here did not create project store under XDG_DATA_HOME")

        # init with no flag, --here, or --global always creates MEMORY_DIR and writes --global config hint
        for idx, init_args in enumerate((["init"], ["init", "--here"], ["--here", "init"],
                                         ["init", "--global"], ["--global", "init"])):
            g_i = os.path.join(base, "init-g-%d" % idx)
            xdg_i = os.path.join(base, "init-xdg-%d" % idx)
            env_i = dict(os.environ, HOME=base, XDG_DATA_HOME=xdg_i, MEMORY_DIR=g_i)
            ri = sub(init_args, env_i, cwd=repo1)
            check(ri.returncode == 0 and os.path.isdir(g_i)
                  and os.path.exists(os.path.join(g_i, "config")),
                  "%r did not create MEMORY_DIR: %s" % (init_args, ri.stderr))
            check(not os.path.exists(xdg_i),
                  "%r should not create project store" % (init_args,))
            cfg_text = open(os.path.join(g_i, "config")).read()
            check("--global config NAME=VALUE" in cfg_text,
                  "%r wrote unscoped config hint: %s" % (init_args, cfg_text))

        # Initialized MEMORY_DIR + XDG_DATA_HOME: --global hits MEMORY_DIR, --here hits XDG, bare wake prints both
        g_live = os.path.join(base, "live-global")
        env_live = dict(os.environ, HOME=base, XDG_DATA_HOME=xdg_dir, MEMORY_DIR=g_live)
        check(sub(["init"], env_live, cwd=repo2).returncode == 0, "init live-global failed")
        check(sub(["note", "--global", "global secret in memory_dir"], env_live, cwd=repo2).returncode == 0,
              "note --global into MEMORY_DIR failed")
        check(sub(["note", "--here", "project fact in xdg"], env_live, cwd=repo2).returncode == 0,
              "note --here with MEMORY_DIR set failed")
        check("global secret in memory_dir" in open(os.path.join(g_live, "LOG.txt")).read(),
              "--global note did not land in MEMORY_DIR")
        check("project fact in xdg" not in open(os.path.join(g_live, "LOG.txt")).read(),
              "--here note leaked into MEMORY_DIR")
        check("project fact in xdg" in open(p2_log).read(),
              "--here note did not land in XDG_DATA_HOME project store")

        both = sub(["wake"], env_live, cwd=repo2)
        check(both.returncode == 0
              and "== Global memory:" in both.stdout
              and "global secret in memory_dir" in both.stdout
              and "== Project memory:" in both.stdout
              and "project fact in xdg" in both.stdout
              and both.stdout.index("global secret in memory_dir") < both.stdout.index("project fact in xdg")
              and "You are awake." in both.stdout.splitlines(),
              "bare wake with MEMORY_DIR set did not print both memories in order:\n" + both.stdout + both.stderr)

        g_only = sub(["wake", "--global"], env_live, cwd=repo2)
        check(g_only.returncode == 0
              and "global secret in memory_dir" in g_only.stdout
              and "project fact in xdg" not in g_only.stdout,
              "wake --global should print only global memory:\n" + g_only.stdout)

        # Global store knob override does not leak into project store during bare wake
        for i in range(2, 4):
            check(sub(["note", "--here", "proj line %d" % i], env_live, cwd=repo2).returncode == 0,
                  "project note %d failed" % i)
        check(sub(["nap", "--here", "0-1", "p01"], env_live, cwd=repo2).returncode == 0,
              "project nap 0-1 failed")
        check(sub(["nap", "--here", "2-3", "p23"], env_live, cwd=repo2).returncode == 0,
              "project nap 2-3 failed")
        check(sub(["nap", "--here", "0-3", "p03"], env_live, cwd=repo2).returncode == 0,
              "project nap 0-3 failed")
        check(sub(["config", "--global", "WAKE_LINES=2"], env_live, cwd=repo2).returncode == 0,
              "global config WAKE_LINES=2 failed")
        bw_iso = sub(["wake"], env_live, cwd=repo2)
        proj_part = bw_iso.stdout.split("== Project memory:", 1)[-1]
        check(bw_iso.returncode == 0
              and all(("#%d " % i) in proj_part for i in range(4))
              and "#0-1 " not in proj_part,
              "global WAKE_LINES=2 leaked into project bare wake:\n" + bw_iso.stdout)

        # In-process re-entrancy: cli.main(argv) resets scope, tool prefix, and knobs
        s1 = os.path.join(base, "store1")
        s2 = os.path.join(base, "store2")
        for sdir in (s1, s2):
            env_s = dict(os.environ, HOME=base, XDG_DATA_HOME=xdg_dir, MEMORY_DIR=sdir)
            check(sub(["init"], env_s, cwd=repo2).returncode == 0,
                  "in-process store init failed")
            for i in range(4):
                check(sub(["note", "--global", "item %d" % i], env_s, cwd=repo2).returncode == 0,
                      "in-process seed note failed")
            check(sub(["nap", "--global", "0-1", "s01"], env_s, cwd=repo2).returncode == 0,
                  "in-process seed nap 0-1 failed")
            check(sub(["nap", "--global", "2-3", "s23"], env_s, cwd=repo2).returncode == 0,
                  "in-process seed nap 2-3 failed")
            check(sub(["nap", "--global", "0-3", "s03"], env_s, cwd=repo2).returncode == 0,
                  "in-process seed nap 0-3 failed")
        check(sub(["config", "--global", "WAKE_LINES=2"],
                  dict(os.environ, HOME=base, XDG_DATA_HOME=xdg_dir, MEMORY_DIR=s1),
                  cwd=repo2).returncode == 0,
              "s1 config WAKE_LINES=2 failed")

        r1 = run("wake", store=s1)
        check(r1.returncode == 0 and "#0-1 " in r1.stdout,
              "cli.main(argv) did not read s1 with WAKE_LINES=2:\n" + r1.stdout + r1.stderr)
        r2 = run("wake", store=s2)
        check(r2.returncode == 0
              and all(("#%d " % i) in r2.stdout for i in range(4))
              and "#0-1 " not in r2.stdout,
              "cli.main(argv) leaked WAKE_LINES=2 from prior call:\n" + r2.stdout + r2.stderr)
        r3 = run("zoom", store=s2)
        check(r3.returncode == 1
              and "--global --global" not in r3.stderr
              and ("usage: %s --global zoom <lo>-<hi>" % cli.pretty(MEMO)) in r3.stderr,
              "cli.main(argv) duplicated --global in ME:\n" + r3.stderr)
    finally:
        shutil.rmtree(base)


# ---- printed command contracts and wake scope ----


def test_wake_and_printed_commands():
    """memo --here wake exits 1 and changes nothing; bare wake prints --here on
    project note/nap/forget hints, keeps paging and wake-again lines bare (no
    --here), prints --global on global hints/paging; zoom past end uses bare
    wake for --here and --global wake for --global; printed nap commands execute
    as printed with PATH=/usr/bin:/bin."""
    base = tempfile.mkdtemp(prefix="optmem-wake-commands-")
    try:
        xdg_dir = os.path.join(base, "xdg")
        g_dir = os.path.join(base, "global")
        fresh_repo = os.path.join(base, "fresh-repo")
        os.makedirs(fresh_repo)
        subprocess.run(["git", "init", "-q", fresh_repo], check=True)
        subprocess.run(["git", "-C", fresh_repo, "remote", "add", "origin",
                        "git@github.com:demo/printed-cmds.git"], check=True)
        env = dict(os.environ, HOME=base, XDG_DATA_HOME=xdg_dir, MEMORY_DIR=g_dir)
        check(sub(["init"], env, cwd=fresh_repo).returncode == 0, "wake setup init failed")

        proj_store = os.path.join(xdg_dir, "optmem", "repo", "demo", "printed-cmds")
        # wake never takes --here (or --here --global)
        exe = cli.pretty(MEMO)
        for bad_wake in (["--here", "wake"], ["wake", "--here"],
                         ["--here", "--global", "wake"], ["wake", "1", "--here"]):
            rw = sub(bad_wake, env, cwd=fresh_repo)
            check(rw.returncode == 1 and not rw.stdout
                  and "does not take --here" in rw.stderr
                  and ("`%s wake`" % exe) in rw.stderr
                  and ("`%s wake --global`" % exe) in rw.stderr,
                  "%r should reject --here with wake guidance: %r / %r"
                  % (bad_wake, rw.stdout, rw.stderr))
            check(not os.path.exists(proj_store),
                  "%r created project store" % (bad_wake,))

        # Empty bare wake: global half hints --global note, project half hints --here note
        empty_w = sub(["wake"], env, cwd=fresh_repo)
        check(empty_w.returncode == 0
              and "--global note" in empty_w.stdout
              and "--here note" in empty_w.stdout,
              "empty bare wake hints missing scopes:\n" + empty_w.stdout)

        # Printed nap commands from both scopes run as printed with minimal PATH
        bare_env = dict(env, PATH="/usr/bin:/bin")
        sub(["note", "--here", "p0"], bare_env, cwd=fresh_repo)
        p_asked = sub(["note", "--here", "p1"], bare_env, cwd=fresh_repo)
        p_order = [l[5:] for l in p_asked.stdout.splitlines() if l.startswith("Run: ")]
        check(len(p_order) == 1 and "--here nap 0-1" in p_order[0],
              "project note did not print --here nap order: " + p_asked.stdout)
        p_run = subprocess.run(p_order[0].replace('"<your line>"', '"p0 and p1"'),
                               shell=True, cwd=fresh_repo, env=bare_env,
                               capture_output=True, text=True)
        check(p_run.returncode == 0 and "0-1 saved." in p_run.stdout,
              "printed --here nap did not run: %r -> %s" % (p_order[0], p_run.stderr))

        sub(["note", "--global", "g0"], bare_env, cwd=fresh_repo)
        g_asked = sub(["note", "--global", "g1"], bare_env, cwd=fresh_repo)
        g_order = [l[5:] for l in g_asked.stdout.splitlines() if l.startswith("Run: ")]
        check(len(g_order) == 1 and "--global nap 0-1" in g_order[0],
              "global note did not print --global nap order: " + g_asked.stdout)
        g_run = subprocess.run(g_order[0].replace('"<your line>"', '"g0 and g1"'),
                               shell=True, cwd=fresh_repo, env=bare_env,
                               capture_output=True, text=True)
        check(g_run.returncode == 0 and "0-1 saved." in g_run.stdout,
              "printed --global nap did not run: %r -> %s" % (g_order[0], g_run.stderr))

        # Trailing nap prompt in bare wake carries --here for project and runs as printed
        sub(["note", "--here", "p2"], bare_env, cwd=fresh_repo)
        sub(["note", "--here", "p3"], bare_env, cwd=fresh_repo)
        tw = sub(["wake"], bare_env, cwd=fresh_repo)
        tw_orders = [l[5:] for l in tw.stdout.splitlines() if l.startswith("Run: ")]
        check(tw.returncode == 0 and len(tw_orders) == 1 and "--here nap 2-3" in tw_orders[0],
              "bare wake trailing nap missing --here: " + tw.stdout)
        tw_run = subprocess.run(tw_orders[0].replace('"<your line>"', '"p2 and p3"'),
                                shell=True, cwd=fresh_repo, env=bare_env,
                                capture_output=True, text=True)
        check(tw_run.returncode == 0 and "2-3 saved." in tw_run.stdout,
              "bare wake trailing nap order failed: %r -> %s" % (tw_orders[0], tw_run.stderr))
        sub(["nap", "--here", "0-3", "all p"], bare_env, cwd=fresh_repo)

        # Bare wake project pagination stays `memo wake 2 <T>` (NO --here!) and executes
        sub(["config", "--here", "PART_LINES=2"], bare_env, cwd=fresh_repo)
        pw1 = sub(["wake"], bare_env, cwd=fresh_repo)
        page_orders = [l.split("Run: ", 1)[1] for l in pw1.stdout.splitlines()
                       if l.startswith("Not awake yet. Run: ")]
        check(pw1.returncode == 0 and len(page_orders) == 1
              and re.search(r"memo wake 2 \d+$", page_orders[0])
              and "--here" not in page_orders[0],
              "bare wake paging line must be bare `memo wake 2 <T>`: " + pw1.stdout)
        pw2 = subprocess.run(page_orders[0], shell=True, cwd=fresh_repo, env=bare_env,
                             capture_output=True, text=True)
        check(pw2.returncode == 0 and pw2.stdout.rstrip().endswith("You are awake."),
              "bare wake paging order failed: %r -> %s" % (page_orders[0], pw2.stderr))
        sub(["config", "--here", "PART_LINES="], bare_env, cwd=fresh_repo)

        # Blocking refusal on bare wake: wake-again is bare, nap carries --here
        sub(["config", "--here", "WAKE_LINES=2"], bare_env, cwd=fresh_repo)
        sub(["forget", "--here", "0-1"], bare_env, cwd=fresh_repo)
        bw_ref = sub(["wake"], bare_env, cwd=fresh_repo)
        check(bw_ref.returncode == 1
              and re.search(r"then run \S*memo wake again\.", bw_ref.stdout)
              and "--here wake" not in bw_ref.stdout
              and "--here nap 0-1" in bw_ref.stdout,
              "bare wake refusal must keep wake bare and scope nap with --here:\n" + bw_ref.stdout)

        # Blank summary on bare wake: forget carries --here
        check(sub(["nap", "--here", "0-1", "p01"], bare_env, cwd=fresh_repo).returncode == 0,
              "nap 0-1 rebuild failed")
        check(sub(["nap", "--here", "2-3", "p23"], bare_env, cwd=fresh_repo).returncode == 0,
              "nap 2-3 rebuild failed")
        check(sub(["nap", "--here", "0-3", "all p"], bare_env, cwd=fresh_repo).returncode == 0,
              "nap 0-3 rebuild failed")
        with open(os.path.join(proj_store, "TREE", "2"), "r+b") as f:
            f.write(b" " * 287 + b"\n")
        bw_blank = sub(["wake"], bare_env, cwd=fresh_repo)
        check(bw_blank.returncode == 1 and "--here forget 0-1" in bw_blank.stderr,
              "bare wake blank summary must print --here forget: " + bw_blank.stderr)
        sub(["forget", "--here", "0-1"], bare_env, cwd=fresh_repo)
        sub(["nap", "--here", "0-1", "p01"], bare_env, cwd=fresh_repo)
        sub(["nap", "--here", "2-3", "p23"], bare_env, cwd=fresh_repo)
        sub(["nap", "--here", "0-3", "all p"], bare_env, cwd=fresh_repo)
        sub(["config", "--here", "WAKE_LINES="], bare_env, cwd=fresh_repo)

        # Global pagination during bare wake keeps --global wake 2 <T> and stops before project
        sub(["note", "--global", "g2"], bare_env, cwd=fresh_repo)
        sub(["note", "--global", "g3"], bare_env, cwd=fresh_repo)
        sub(["nap", "--global", "2-3", "g23"], bare_env, cwd=fresh_repo)
        sub(["nap", "--global", "0-3", "all g"], bare_env, cwd=fresh_repo)
        sub(["config", "--global", "PART_LINES=2"], bare_env, cwd=fresh_repo)
        gw1 = sub(["wake"], bare_env, cwd=fresh_repo)
        g_page = [l.split("Run: ", 1)[1] for l in gw1.stdout.splitlines()
                  if l.startswith("Not awake yet. Run: ")]
        check(gw1.returncode == 0 and len(g_page) == 1
              and re.search(r"memo --global wake 2 \d+$", g_page[0])
              and "== Project memory:" not in gw1.stdout,
              "global paging in bare wake must print --global wake 2 <T>:\n" + gw1.stdout)
        gw2 = subprocess.run(g_page[0], shell=True, cwd=fresh_repo, env=bare_env,
                             capture_output=True, text=True)
        check(gw2.returncode == 0 and gw2.stdout.rstrip().endswith("You are awake."),
              "global paging order failed: %r -> %s" % (g_page[0], gw2.stderr))

        # zoom past end: --here prints bare wake, --global prints --global wake
        zh_past = sub(["zoom", "--here", "1048576-2097151"], bare_env, cwd=fresh_repo)
        check(zh_past.returncode == 1
              and re.search(r"Run: \S*memo wake$", zh_past.stderr.strip())
              and "--here wake" not in zh_past.stderr,
              "zoom --here past end must print bare wake: " + zh_past.stderr)
        zg_past = sub(["zoom", "--global", "1048576-2097151"], bare_env, cwd=fresh_repo)
        check(zg_past.returncode == 1
              and re.search(r"Run: \S*memo --global wake$", zg_past.stderr.strip()),
              "zoom --global past end must print --global wake: " + zg_past.stderr)
    finally:
        shutil.rmtree(base)


# ---- CLI help and usage ----


def test_cli_help():
    """-h, --help anywhere in argv and `memo help` print module usage to stdout,
    exit 0, leave existing stores byte-identical, and create no store directory
    in a fresh project."""
    base = tempfile.mkdtemp(prefix="optmem-help-flags-")
    try:
        xdg_dir = os.path.join(base, "xdg")
        missing_g = os.path.join(base, "missing-global")
        repo_dir = os.path.join(base, "repo")
        os.makedirs(repo_dir)
        subprocess.run(["git", "init", "-q", repo_dir], check=True)
        subprocess.run(["git", "-C", repo_dir, "remote", "add", "origin",
                        "git@github.com:demo/helpcheck.git"], check=True)
        env = dict(os.environ, HOME=base, XDG_DATA_HOME=xdg_dir, MEMORY_DIR=missing_g)

        help_cases = [
            ["-h"],
            ["--help"],
            ["help"],
            ["note", "--help"],
            ["note", "--here", "-h"],
            ["--here", "--global", "--help"],
            ["--here", "help"],
            ["--global", "help"],
        ]
        for args in help_cases:
            r = sub(args, env, cwd=repo_dir)
            check(r.returncode == 0 and not r.stderr
                  and "OptMem:" in r.stdout,
                  "help invocation %r failed: rc=%d out=%r err=%r"
                  % (args, r.returncode, r.stdout, r.stderr))
            check(not os.path.exists(xdg_dir),
                  "help %r created XDG store directory" % (args,))
            check(not os.path.exists(missing_g),
                  "help %r created MEMORY_DIR" % (args,))

        # On existing stores, help leaves every byte unchanged
        check(sub(["init"], env, cwd=repo_dir).returncode == 0, "help setup init failed")
        check(sub(["note", "--here", "stay intact"], env, cwd=repo_dir).returncode == 0,
              "help setup note --here failed")
        check(sub(["note", "--global", "stay intact global"], env, cwd=repo_dir).returncode == 0,
              "help setup note --global failed")
        proj_store = os.path.join(xdg_dir, "optmem", "repo", "demo", "helpcheck")
        p_fp = fingerprint(proj_store)
        g_fp = fingerprint(missing_g)
        for args in (["note", "--help"], ["note", "--here", "--help"],
                     ["note", "--global", "-h"], ["--help"], ["-h"], ["help"]):
            r = sub(args, env, cwd=repo_dir)
            check(r.returncode == 0 and not r.stderr and "OptMem:" in r.stdout,
                  "help %r on live store failed" % (args,))
        check(fingerprint(proj_store) == p_fp, "help modified project store")
        check(fingerprint(missing_g) == g_fp, "help modified global store")
    finally:
        shutil.rmtree(base)


test_scope_flag_policy()
test_exact_flag_tokens()
test_store_routing()
test_wake_and_printed_commands()
test_cli_help()

# A path-local store keyed by a symlink spelling is still on disk after
# path_slug starts resolving links. The relink script shows the move and
# writes only with --move. It must not overwrite a store, and it must not
# move a store whose resolved path is missing.


def unresolved_slug(p):
    """The path/ key from before realpath: abspath, then the same split."""
    p = os.path.normcase(os.path.abspath(p))
    return os.path.join("path", *[b for b in p.split(os.sep) if b])


def plant_store(xdg_root, slug, text):
    store = os.path.join(xdg_root, "optmem", slug)
    os.makedirs(os.path.join(store, "TREE"))
    with open(os.path.join(store, "LOG.txt"), "w") as fh:
        fh.write(text)
    return store


def run_relink(xdg_root, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, "relink-path-stores"), *args],
                          capture_output=True, text=True,
                          env=dict(os.environ, XDG_DATA_HOME=xdg_root))


relink = SourceFileLoader("relink_path_stores",
                           os.path.join(HERE, "relink-path-stores")).load_module()
win_slug = cli.path_slug(r"C:\work\real-dir", path=ntpath)
win_back = relink.filesystem_path(win_slug.split(ntpath.sep)[1:], ntpath)
check(cli.path_slug(win_back, path=ntpath) == win_slug,
      "a Windows path/ key did not rebuild the same path: " + win_back)
unc_slug = cli.path_slug(r"\\server\share\proj", path=ntpath)
unc_back = relink.filesystem_path(unc_slug.split(ntpath.sep)[1:], ntpath)
check(cli.path_slug(unc_back, path=ntpath) == unc_slug,
      "a UNC path/ key did not rebuild the same path: " + unc_back)

fs = tempfile.mkdtemp(prefix="optmem-relink-fs-")
real = os.path.join(fs, "real-dir")
os.mkdir(real)
link = os.path.join(fs, "link-name")
os.symlink("real-dir", link)
other = os.path.join(fs, "other-link")
os.symlink("real-dir", other)
dangling = os.path.join(fs, "dangling-link")
os.symlink(os.path.join(fs, "missing-target"), dangling)
plain = os.path.join(fs, "plain-dir")
os.mkdir(plain)

relink_xdg = tempfile.mkdtemp(prefix="optmem-relink-xdg-")
old_store = plant_store(relink_xdg, unresolved_slug(link), "from-the-link\n")
plant_store(relink_xdg, os.path.join("repo", "acme", "widget"), "repo-kept\n")
kept_repo = os.path.join(relink_xdg, "optmem", "repo", "acme", "widget", "LOG.txt")
dry = run_relink(relink_xdg)
check(dry.returncode == 0, "dry run failed: " + dry.stderr)
check("would move" in dry.stdout, "dry run did not show the move: " + dry.stdout)
check(dry.stdout.count("link-name") == 1,
      "the symlink spelling was printed twice: " + dry.stdout)
check("from-the-link\n" == open(os.path.join(old_store, "LOG.txt")).read(),
      "dry run rewrote the store")
check(not os.path.exists(os.path.join(relink_xdg, "optmem", cli.path_slug(real), "LOG.txt")),
      "dry run created the resolved store")
check("repo-kept" not in dry.stdout, "dry run listed a repo store: " + dry.stdout)

moved = run_relink(relink_xdg, "--move")
new_log = os.path.join(relink_xdg, "optmem", cli.path_slug(link), "LOG.txt")
check(moved.returncode == 0, "move failed: " + moved.stderr)
check(os.path.exists(new_log) and open(new_log).read() == "from-the-link\n",
      "the link store did not arrive on the resolved path")
check(not os.path.exists(os.path.join(old_store, "LOG.txt")),
      "the old spelling still holds the log")
check(open(kept_repo).read() == "repo-kept\n", "a repo store was touched")

clash_xdg = tempfile.mkdtemp(prefix="optmem-relink-clash-")
plant_store(clash_xdg, unresolved_slug(link), "from-the-link\n")
plant_store(clash_xdg, unresolved_slug(other), "from-the-other\n")
plant_store(clash_xdg, cli.path_slug(real), "already-there\n")
clash = run_relink(clash_xdg, "--move")
check(clash.returncode == 0, "clash move failed: " + clash.stderr)
check("left in place" in clash.stdout, "a clash was not reported: " + clash.stdout)
check(open(os.path.join(clash_xdg, "optmem", cli.path_slug(real), "LOG.txt")).read()
      == "already-there\n", "the resolved store was overwritten")
check(open(os.path.join(clash_xdg, "optmem", unresolved_slug(link), "LOG.txt")).read()
      == "from-the-link\n", "the link store was removed during a clash")
check(open(os.path.join(clash_xdg, "optmem", unresolved_slug(other), "LOG.txt")).read()
      == "from-the-other\n", "the other link store was removed during a clash")

both_xdg = tempfile.mkdtemp(prefix="optmem-relink-both-")
plant_store(both_xdg, unresolved_slug(link), "from-the-link\n")
plant_store(both_xdg, unresolved_slug(other), "from-the-other\n")
both = run_relink(both_xdg, "--move")
check(both.returncode == 0, "two spellings failed: " + both.stderr)
arrived = open(os.path.join(both_xdg, "optmem", cli.path_slug(real), "LOG.txt")).read()
check(arrived in ("from-the-link\n", "from-the-other\n"),
      "neither spelling arrived: " + arrived)
survivors = []
for spelling in (link, other):
    log = os.path.join(both_xdg, "optmem", unresolved_slug(spelling), "LOG.txt")
    if os.path.exists(log):
        survivors.append(open(log).read())
check(len(survivors) == 1 and survivors[0] != arrived,
      "one spelling was lost: arrived %r survivors %r" % (arrived, survivors))

dangling_xdg = tempfile.mkdtemp(prefix="optmem-relink-dangling-")
plant_store(dangling_xdg, unresolved_slug(dangling), "still-here\n")
dangling_run = run_relink(dangling_xdg, "--move")
check(dangling_run.returncode == 0, "dangling move failed: " + dangling_run.stderr)
check(open(os.path.join(dangling_xdg, "optmem", unresolved_slug(dangling), "LOG.txt")).read()
      == "still-here\n", "a dangling link store was moved")
check("left in place" in dangling_run.stdout,
      "a dangling link was not reported: " + dangling_run.stdout)

plain_xdg = tempfile.mkdtemp(prefix="optmem-relink-plain-")
plant_store(plain_xdg, cli.path_slug(plain), "plain\n")
plain_run = run_relink(plain_xdg)
check(plain_run.returncode == 0 and plain_run.stdout.strip() == "Nothing to move.",
      "a resolved store was listed: " + plain_run.stdout)

bad = run_relink(plain_xdg, "--apply")
check(bad.returncode == 2, "an unknown flag was accepted")
check(open(os.path.join(plain_xdg, "optmem", cli.path_slug(plain), "LOG.txt")).read()
      == "plain\n", "an unknown flag wrote the store")

for leftover in (fs, relink_xdg, clash_xdg, both_xdg, dangling_xdg, plain_xdg):
    shutil.rmtree(leftover)

print("\n%d passed, %d failed" % (ok, fail))
sys.exit(1 if fail else 0)
