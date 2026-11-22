# Reads Polestar's playtest output and records, in ci_data.json, the quests the simulated player could not hand in
# because no goal of the guide works one of their objectives ("needs_work"). emit_guide.py then writes a whole-quest
# `complete` for them (never split into objectives that miss one) and puts one before a hand-in that has none.
#   python3 read_playtest.py <playtest-nood.txt>
import re, sys, json, os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ci_data.json')
d = json.load(open(out)) if os.path.exists(out) else {}
need = set(d.get('needs_work', []))
for l in open(sys.argv[1], encoding='utf-8'):
    m = re.search(r'the game takes no hand-in of quest (\d+)', l)
    if m:
        need.add(int(m.group(1)))
d['needs_work'] = sorted(need)
json.dump(d, open(out, 'w'), indent=0)
print('needs_work', d['needs_work'])
