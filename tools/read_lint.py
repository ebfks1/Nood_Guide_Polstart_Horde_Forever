# Reads `forge guide lint` text output and writes ci_data.json: what the official data build knows differently
# from the tables the converter reads (ids it lacks, the quest log's objective order).
#   python3 read_lint.py <lint-nood.txt> [--keep-order]
import re, sys, json, os, collections
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ci_data.json')
old = json.load(open(out)) if os.path.exists(out) else {}
unk = collections.defaultdict(set)
# the repo the lint ran on: its guide lines name the quest of an elite warning
GUIDES = os.environ.get('NOOD_REPO', '/home/claude/nood_guide_polstart_horde_forever')
pre = collections.defaultdict(set)
elite = set(old.get('elite', []))
blocked = set(old.get('race_blocked', []))
root = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[1])))
for q, v in old.get('prereq', {}).items():
    pre[int(q)] |= set(v)
order = {int(q): {int(a): b for a, b in m.items()} for q, m in old.get('objorder', {}).items()}
for l in open(sys.argv[1], encoding='utf-8'):
    m = re.match(r'^(\S+?):(\d+): (error|warning): (.*)$', l)
    if not m:
        continue
    msg = m.group(4)
    if ('elite' in msg and ('`kill`' in msg or '`collect`' in msg)) or 'yards from every known spawn' in msg:
        # the quest of that goal line: whole-quest goals stay whole for it (a dungeon quest, done in a group)
        src = os.path.join(GUIDES, m.group(1)) if GUIDES else None
        try:
            ln = open(src, encoding='utf-8').read().split('\n')[int(m.group(2)) - 1]
            qm = re.search(r'quest (\d+)\.', ln)
            if qm:
                elite.add(int(qm.group(1)))
        except (OSError, IndexError, TypeError):
            pass
        continue
    rb = re.match(r'quest (\d+) \(.*\) is not available to any race this (?:step|goal) applies to', msg)
    if rb:
        blocked.add(int(rb.group(1)))
        continue
    n = re.match(r'quest (\d+) needs (\d+) \(.*?\) turned in first', msg)
    if n:
        pre[int(n.group(1))].add(int(n.group(2)))
        continue
    u = re.match(r'(quest|npc|item|object) (\d+) is not in data', msg)
    if u:
        unk[u.group(1)].add(int(u.group(2)))
        continue
    o = re.match(r'quest (\d+)\.(\d+) is .*?, not this (?:npc|item|object)(?:; .* is \d+\.(\d+))?', msg)
    if o and o.group(3):
        q, shown, true = int(o.group(1)), int(o.group(2)), int(o.group(3))
        # `shown` is what the converter wrote (already mapped); undo that to get this file's own number
        mine = next((a for a, b in order.get(q, {}).items() if b == shown), shown)
        order.setdefault(q, {})[mine] = true
for k, v in old.get('unknown', {}).items():
    if '--fresh' not in sys.argv:
        unk[k] |= set(v)
json.dump({'unknown': {k: sorted(v) for k, v in unk.items()}, 'objorder': order, 'prereq': {q: sorted(v) for q, v in pre.items()}, 'elite': sorted(elite), 'race_blocked': sorted(blocked)}, open(out, 'w'), indent=0)
print({k: len(v) for k, v in unk.items()}, len(order), 'quests with another objective order')
