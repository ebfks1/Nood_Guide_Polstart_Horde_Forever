# BalCon (Guidelime) -> Polestar community addon. Own converter; the output follows docs/PACK_FORMAT.md.
import re, sys, os, glob, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psdata import DB, dist

SRC = '/home/claude/ebfks1/balcon_guidlime_horde_forever'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/out'
PACK_ID = 'nood'
FOLDER = 'PolestarPack_Nood'
SRC_VERSION = '1.2.2'
VERSION = '1.0.0-test1'

db = DB()
db.zones['Stonetalon Mountains'] = 1442

GUIDES = [
    ('01_1-12_Durotar', '01-durotar', ['Orc', 'Troll'], 1411, 'Durotar'),
    ('02_1-12_Mulgore', '02-mulgore', ['Tauren'], 1412, 'Mulgore'),
    ('03_1-12_Tirisfal', '03-tirisfal', ['Scourge'], 1420, 'Tirisfal Glades'),
    ('04_1-12_Zephras', '04-zephras', ['Skyborne'], 2521, 'Zephras Isle'),
    ('05_12-25_BalCon', '05-12-25', None, 1454, 'Orgrimmar'),
    ('06_25-30_BalCon', '06-25-30', None, 1440, 'Ashenvale'),
    ('07_30-40_BalCon', '07-30-40', None, 1456, 'Thunder Bluff'),
    ('08_40-50_BalCon', '08-40-50', None, 1458, 'Undercity'),
    ('09_50-60_BalCon', '09-50-60', None, 1454, 'Orgrimmar'),
]
RACES = {'orc': 'Orc', 'troll': 'Troll', 'tauren': 'Tauren', 'undead': 'Scourge', 'skyborne': 'Skyborne'}
CLASSES = {c.lower(): c.upper() for c in ['Warrior', 'Paladin', 'Hunter', 'Rogue', 'Priest', 'Shaman', 'Mage', 'Warlock', 'Druid']}

# ---- BalCon's own level rule (00_AutoSkip.lua): quest level + 4 --------------------------------------
auto = open(SRC + '/00_AutoSkip.lua', encoding='utf-8').read()
MARGIN = int(re.search(r'G\.MARGIN = (\d+)', auto).group(1))
QLV = {int(a): int(b) for a, b in re.findall(r'\[(\d+)\]=(\d+)', re.search(r'G\.QLV = \{(.*?)\}\n', auto, re.S).group(1))}
KEEP = {int(a) for a in re.findall(r'\[(\d+)\]=true', re.search(r'G\.KEEP = \{(.*?)\}\n', auto, re.S).group(1))}
CLEAN = [(int(q), int(l)) for q, l in re.findall(r'\{q = (\d+), lvl = (\d+)', auto)]

TAG = re.compile(r'\[(QA|QT|QC|QS|OC|XP|GA|NX|Q|O|N|D|G|L|A|F|P|H|S|T|V|R)([^\]]*)\]')
COORD = re.compile(r'^\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*(.*)$')
IMPORTANT = re.compile(r'^\s*(──|==|★|\*|※|!|▶|>>)')

report = collections.Counter()
notes_log = []


def body(path):
    s = open(path, encoding='utf-8').read()
    a = s.index('Guidelime.registerGuide([[') + len('Guidelime.registerGuide([[')
    b = s.rindex(']]')
    return s[a:b].split('\n')


def tokens(line):
    """-> [('text', s) | ('tag', code, arg)]; a bracket that is no tag stays text."""
    out, pos = [], 0
    for m in TAG.finditer(line):
        code, arg = m.group(1), m.group(2)
        ok = True
        if code in ('G', 'L'):
            ok = COORD.match(arg) is not None
        elif code in ('O', 'OC', 'T', 'V', 'R'):
            ok = arg.strip() == ''
        elif code in ('QA', 'QT', 'QC', 'QS', 'Q'):
            ok = re.match(r'^\s*\d+', arg) is not None
        elif code == 'XP':
            ok = re.match(r'^\d', arg) is not None
        elif code == 'A':
            names = [n.strip().lower() for n in arg.split(',') if n.strip()]
            ok = bool(names) and all(n in RACES or n in CLASSES for n in names)
        elif code in ('F', 'P', 'H', 'S'):
            ok = arg.startswith(' ') and arg.strip() != ''
        if not ok:
            continue
        if m.start() > pos:
            out.append(('text', line[pos:m.start()]))
        out.append(('tag', code, arg))
        pos = m.end()
    if pos < len(line):
        out.append(('text', line[pos:]))
    return out


LEVEL12 = ('! At level 12 we recommend ending this guide here and moving on to the 12-25 Nood guide: pick it in Polestar\'s guide menu. Quests you leave undone here give no reputation.',
           '※ 12레벨이 되면 이 가이드를 여기서 마치고 12-25 Nood 가이드로 넘어가는 것을 권장합니다. Polestar 가이드 메뉴에서 "12-25 Nood"를 고르세요. 여기 남긴 퀘스트의 평판은 받지 못합니다.')


def clean(s):
    s = re.sub(r'\|c[0-9A-Fa-f]{8}', '', s).replace('|r', '').replace('|', '')
    s = re.sub(r'\((확인했으면 눌러 닫기|click to close once checked|click to close)\)', '', s)
    s = re.sub(r'\(\s*\)', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s+([.,:;)])', r'\1', s)
    return s


def display(toks, spaced=False):
    parts = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t[0] == 'text':
            parts.append(t[1])
        else:
            code, arg = t[1], t[2]
            word = None
            if code in ('QA', 'QT', 'QC', 'QS', 'Q'):
                word = re.sub(r'^\s*\d+(,\d+)?\s*', '', arg)
            elif code in ('F', 'P', 'H', 'S'):
                word = arg.strip()
                rest = ''.join(x[1] for x in toks[i + 1:] if x[0] == 'text').strip()
                before = ''.join(x[1] for x in toks[:i] if x[0] == 'text').rstrip()
                if not rest and before and before[-1] in '.)!':
                    word = None
            elif code == 'XP':
                word = re.sub(r'^\S+\s*', '', arg)
            if word:
                if spaced:
                    prev = parts[-1] if parts else ''
                    nxt = toks[i + 1][1] if i + 1 < n and toks[i + 1][0] == 'text' else ''
                    if prev and (prev[-1].isalnum() or prev[-1] in ',:'):
                        word = ' ' + word
                    if nxt and nxt[0].isalnum():
                        word = word + ' '
                parts.append(word)
    return clean(''.join(parts))


def bare(toks):
    """The line's own words without quest titles: is there a tip worth showing?"""
    parts = [t[1] for t in toks if t[0] == 'text']
    s = clean(''.join(parts))
    s = re.sub(r'(?i)\b(accept|turn in|turn it in|finish|work on|then|next|also|and|the follow-up|to)\b', '', s)
    s = re.sub(r'(수락|완료|퀘스트|이어서|그리고|진행|마무리|하세요|:)', '', s)
    s = re.sub(r'[\s.,:;\-—·()]+', '', s)
    return s


class Line:
    def __init__(self, en, ko):
        self.en_raw, self.ko_raw = en, ko
        self.t = tokens(en)
        self.tk = tokens(ko) if ko is not None else self.t
        self.codes = [t[1] for t in self.t if t[0] == 'tag']
        self.en = display(self.t, True)
        self.ko = display(self.tk) if ko is not None else self.en
        if 'Guidelime' in en and 'D' not in self.codes:
            self.en, self.ko = LEVEL12
        self.oc = 'OC' in self.codes
        self.opt = 'O' in self.codes
        races, classes = [], []
        for t in self.t:
            if t[0] == 'tag' and t[1] == 'A':
                for n in t[2].split(','):
                    n = n.strip().lower()
                    if n in RACES and RACES[n] not in races:
                        races.append(RACES[n])
                    elif n in CLASSES and CLASSES[n] not in classes:
                        classes.append(CLASSES[n])
        self.only = None
        if races or classes:
            self.only = {}
            if classes:
                self.only['classes'] = classes
            if races:
                self.only['races'] = races

    def tags(self, *codes):
        return [t for t in self.t if t[0] == 'tag' and t[1] in codes]

    def ko_title(self, qid, fallback):
        for t in self.tk:
            if t[0] == 'tag' and t[1] in ('QA', 'QT', 'QC', 'Q', 'QS'):
                m = re.match(r'^\s*(\d+)(?:,\d+)?\s*(.*)$', t[2])
                if m and int(m.group(1)) == qid and m.group(2).strip():
                    return m.group(2).strip()
        return fallback


# ---- Lua writer -----------------------------------------------------------------------------------------
def lstr(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '') + '"'


class T:
    def __init__(self, en, ko=None):
        self.en, self.ko = en, ko if (ko and ko != en) else None

    def lua(self):
        return 'T(%s, %s)' % (lstr(self.en), lstr(self.ko)) if self.ko else lstr(self.en)


class Raw:
    def __init__(self, s):
        self.s = s


def lua(v, ind=0):
    if isinstance(v, T):
        return v.lua()
    if isinstance(v, Raw):
        return v.s
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return ('%.2f' % v).rstrip('0').rstrip('.')
    if isinstance(v, str):
        return lstr(v)
    if isinstance(v, list):
        return '{ ' + ', '.join(lua(x) for x in v) + ' }' if v else '{}'
    if isinstance(v, dict):
        return '{ ' + ', '.join('%s = %s' % (k, lua(x)) for k, x in v.items()) + ' }'
    raise TypeError(type(v))


# ---- places ---------------------------------------------------------------------------------------------
def place(mp, x, y):
    d = {'map': mp, 'x': round(x, 2), 'y': round(y, 2)}
    if db.is_era(mp):
        d['f'] = 'e'
    return d


def nearest_cluster(refs, here, prefer_map=None):
    """refs: entity refs -> the cluster nearest `here` (map, x, y), else one on prefer_map, else any."""
    best = None
    for ref in refs:
        e = db.entity(ref)
        if not e:
            continue
        for mp, era, x, y, r in e[1]:
            if here and mp == here[0]:
                score = dist((x, y), (here[1], here[2]))
            elif prefer_map and mp == prefer_map:
                score = 1000
            else:
                score = 5000
            if best is None or score < best[0]:
                best = (score, ref, mp, x, y)
    return best


def objective_refs(q):
    refs = []
    for kind, id, cnt in q['objs']:
        if kind == 1:
            refs.append(id)
        elif kind == 3:
            refs.append(-id)
        elif kind == 2:
            it = db.item(id)
            if it:
                srcs = sorted(it[1], key=lambda s: -s[1])[:4]
                refs += [s[0] for s in srcs]
                refs += [-o[0] for o in sorted(it[2], key=lambda s: -s[1])[:3]]
    return refs


class Guide:
    def __init__(self, stem, slug, races, zone, zone_name):
        self.stem, self.slug, self.races = stem, slug, races
        self.zone, self.zone_name = zone, zone_name
        en, ko = body('%s/%s_en.lua' % (SRC, stem)), body('%s/%s.lua' % (SRC, stem))
        if len(en) != len(ko):
            notes_log.append('%s: Korean and English files have different line counts; English text used' % stem)
            ko = [None] * len(en)
        else:
            ko = list(ko)
            for i, (a, b) in enumerate(zip(en, ko)):
                ca = [t[1] for t in tokens(a) if t[0] == 'tag']
                cb = [t[1] for t in tokens(b) if t[0] == 'tag']
                if ca != cb:
                    notes_log.append('%s line %d: tags differ between Korean and English, English used\n  EN %s\n  KO %s' % (stem, i + 1, a[:160], b[:160]))
                    ko[i] = None
        self.lines = [Line(a, b) for a, b in zip(en, ko)]
        self.autoskip = any('BalConAutoSkip' in l.en_raw for l in self.lines)
        self.steps = []
        self.pending = []  # {'goal': {...}, 'only': ..., 'sticky': bool}
        self.cur_map = zone
        self.here = None
        self.title = self.next = self.desc = None
        self.min = self.max = None
        self.clean_block = {}  # line index -> level
        self.find_clean()

    def find_clean(self):
        for q, lvl in CLEAN:
            at = None
            for i, l in enumerate(self.lines):
                if l.opt and any(re.match(r'^\s*%d\b' % q, t[2]) for t in l.tags('QA')):
                    at = i
                    break
            if at is None:
                continue
            s = e = at
            while s > 0 and self.lines[s - 1].opt:
                s -= 1
            while e < len(self.lines) - 1 and self.lines[e + 1].opt:
                e += 1
            for i in range(s, e + 1):
                self.clean_block[i] = lvl

    # -- coordinates
    def coord(self, arg):
        m = COORD.match(arg)
        x, y, zone = float(m.group(1)), float(m.group(2)), m.group(3).strip()
        if zone:
            mp = db.zones.get(zone)
            if mp is None:
                report['unknown zone ' + zone] += 1
                return None
            self.cur_map = mp
        return (self.cur_map, x, y)

    def gate(self, qid):
        if not self.autoskip or qid in KEEP or qid not in QLV:
            return None
        return QLV[qid] + MARGIN

    def emit(self, step, holding=True, block=None):
        """block: the level of the "before level N" stretch the step belongs to, or None."""
        step['_block'] = block
        whens = step.get('when') or []
        step['_gated'] = any(not (w['k'] == 'level' and w['op'] == '<' and w['n'] == block) for w in whens)
        step['_holds'] = holding
        if holding:
            aud = step.get('only')
            keep = []
            for p in self.pending:
                if p['block'] != block:
                    if p['block'] is None:
                        keep.append(p)  # waits for the stretch to end
                    continue  # a note of a stretch that is over: dropped with it
                fits = aud is None or p['only'] == aud
                if fits and not (p['sticky'] and step['_gated']):
                    self.attach(step, p, front=True)
                else:
                    keep.append(p)
            self.pending = keep
        if step.get('along') and step.get('note') and step['goals']:
            step['goals'][0] = dict(step['goals'][0], note=step.pop('note'))
        self.steps.append(step)

    def attach(self, step, p, front):
        g = dict(p['goal'])
        if p['only'] and step.get('only') is None:
            g['only'] = p['only']
        if front:
            step['goals'].insert(len([x for x in step['goals'] if x.get('_pre')]), dict(g, _pre=True))
        else:
            step['goals'].append(g)

    def add_pending(self, goal, only, sticky, block):
        p = {'goal': goal, 'only': only, 'sticky': sticky, 'block': block}
        if sticky and goal['t'] == 'note':
            # a heading or a warning: if the step after it may be left out, show it on the step before
            self.pending.append(dict(p, _back=len(self.steps)))
        else:
            self.pending.append(p)

    def settle(self):
        """Headings still waiting behind a step that may be left out go to the step before them."""
        keep = []
        for p in self.pending:
            at = p.get('_back')
            if at is None or len(self.steps) <= at:
                keep.append(p)
                continue
            nxt = self.steps[at]
            if not (nxt['_holds'] and nxt['_gated'] or not nxt['_holds'] or nxt['_block'] != p['block'] or (nxt.get('only') and nxt.get('only') != p['only'])):
                keep.append(p)
                continue
            home = None
            for k in range(at - 1, max(-1, at - 8), -1):
                st = self.steps[k]
                if st['_holds'] and not st['_gated'] and st['_block'] == p['block'] and (st.get('only') is None or st.get('only') == p['only']):
                    home = st
                    break
            if home is not None:
                self.attach(home, p, front=False)
            else:
                keep.append(dict(p, _back=None))
        self.pending = keep

    def note(self, line, sticky=None, block=None):
        if not line.en:
            return
        if sticky is None:
            sticky = bool(IMPORTANT.match(line.en))
        self.add_pending({'t': 'note', 'text': T(line.en, line.ko)}, line.only, sticky, block)

    def quest_goal(self, verb, qid, title_en, line, pos, obj=None):
        q = db.quest(qid)
        title_en = title_en or (q and q['title']) or ('Quest %d' % qid)
        g = {'t': verb, 'quest': qid, 'title': T(title_en, line.ko_title(qid, title_en))}
        if q and q['level'] and verb == 'accept':
            g['qlvl'] = int(q['level'])
        loc = None
        if verb in ('accept', 'turnin'):
            refs = (q['start'] if verb == 'accept' else q['finish']) if q else []
            near = nearest_cluster(refs, pos or self.here, q and q['zone']) if refs else None
            if pos:
                loc = pos
                g['_w'] = True
                if near and near[2] == pos[0] and dist((near[3], near[4]), (pos[1], pos[2])) <= 4:
                    self.name_entity(g, near[1])
                    report['%s: giver named' % verb] += 1
                elif near:
                    report['%s: written place kept, data differs' % verb] += 1
            elif near:
                loc = (near[2], near[3], near[4])
                self.name_entity(g, near[1])
                report['%s: place from data' % verb] += 1
                if self.here and near[2] != self.here[0]:
                    notes_log.append('PLACE %s %s %d %s: data says map %d %.1f,%.1f; last place was map %d' % (self.stem, verb, qid, title_en, near[2], near[3], near[4], self.here[0]))
            elif q and verb == 'accept' and q['startItem']:
                si = q['startItem'][0] if isinstance(q['startItem'], list) else q['startItem']
                it = db.item(int(si))
                g['item'] = int(si)
                g['itemName'] = it[0] if it else title_en
                report['accept: starts from an item'] += 1
            else:
                report['%s: no place' % verb] += 1
        else:
            if pos:
                loc = pos
                g['_w'] = True
            elif q:
                near = nearest_cluster(objective_refs(q), self.here, q['zone'])
                if near and near[0] < 5000:
                    loc = (near[2], near[3], near[4])
                    report['complete: place from data'] += 1
                else:
                    report['complete: no place'] += 1
            else:
                report['complete: no place'] += 1
        if loc:
            g.update(place(*loc))
            self.here = loc
        return g

    def name_entity(self, g, ref):
        e = db.entity(ref)
        if not e:
            return
        if ref > 0:
            g['npc'], g['npcName'] = ref, e[0]
        else:
            g['object'], g['objName'] = -ref, e[0]

    def objective_goal(self, qid, oi, title_en, line, pos):
        """[QC id,n]: that one objective, where the data names it."""
        q = db.quest(qid)
        if q and 1 <= oi <= len(q['objs']):
            kind, id, cnt = q['objs'][oi - 1]
            base = {'quest': qid, 'oi': oi, 'title': T(title_en, line.ko_title(qid, title_en))}
            if kind == 1 and db.entity(id):
                g = dict(t='kill', target=db.entity(id)[0], npc=id, count=cnt, **base)
            elif kind == 2 and db.item(id):
                g = dict(t='collect', item=id, itemName=db.item(id)[0], count=cnt, **base)
            elif kind == 3 and db.entity(-id):
                g = dict(t='interact', object=id, objName=db.entity(-id)[0], **base)
            else:
                return None
            loc = pos
            if pos:
                g['_w'] = True
            if not loc:
                refs = [id] if kind == 1 else [-id] if kind == 3 else objective_refs(dict(objs=[(kind, id, cnt)]))
                near = nearest_cluster(refs, self.here, q['zone'])
                if near and near[0] < 5000:
                    loc = (near[2], near[3], near[4])
            if loc:
                g.update(place(*loc))
                self.here = loc
            report['objective goals'] += 1
            return g
        return None

    def convert(self):
        for idx, line in enumerate(self.lines):
            raw = line.en_raw.strip()
            if not raw or raw.startswith('--'):
                continue
            codes = line.codes
            if 'D' in codes:
                def short(x):
                    x = re.sub(r'^(BalCon Dungeon Leveling|발컨 던전 레벨업)[^—]*—\s*', '', clean(x))
                    return x if len(x) <= 230 else x[:228].rstrip() + '…'
                kd = [t for t in line.tk if t[0] == 'tag' and t[1] == 'D']
                self.desc = T(short(line.tags('D')[0][2]), short(kd[0][2]) if kd else None)
                continue
            if 'GA' in codes:
                continue
            if 'N' in codes and 'NX' not in codes:
                n_en = line.tags('N')[0][2].strip()
                n_ko = [t for t in line.tk if t[0] == 'tag' and t[1] == 'N'][0][2].strip()
                m = re.match(r'^(\d+)-(\d+)\s*(.*)$', n_en)
                self.min, self.max = int(m.group(1)), int(m.group(2))
                self.title = T(n_en.replace('BalCon', 'Nood'), n_ko.replace('발컨', 'Nood'))
                continue
            if 'NX' in codes:
                self.next = line.tags('NX')[0][2].strip()
                continue
            self.convert_line(idx, line)
            self.settle()
        # texts left over go to the last step that holds
        if self.pending:
            for step in reversed(self.steps):
                if step['_holds'] and not step.get('when'):
                    for p in self.pending:
                        g = dict(p['goal'])
                        if p['only']:
                            g['only'] = p['only']
                        step['goals'].append(g)
                    break
            self.pending = []
        self.merge_runs()

    def merge_runs(self):
        """Quest work with no place of its own in a row (inside a dungeon): one step, every goal open together."""
        def plain(st):
            if not st['_holds'] or st.get('when') or st.get('only') or st.get('along') or len(st['goals']) != 1:
                return False
            g = st['goals'][0]
            return g['t'] in ('accept', 'turnin', 'complete', 'kill', 'collect', 'interact') and 'map' not in g and not g.get('optional')
        out, run = [], []

        def flush():
            if len(run) >= 2:
                goals = []
                for st in run:
                    g = dict(st['goals'][0])
                    if st.get('note'):
                        g['note'] = st['note']
                    goals.append(g)
                out.append({'goals': goals, '_holds': True, '_block': None, '_gated': False})
                report['steps merged into dungeon checklists'] += len(run)
            else:
                out.extend(run)
            run.clear()
        for st in self.steps:
            if plain(st) and len(run) < 8:
                run.append(st)
            else:
                flush()
                if plain(st):
                    run.append(st)
                else:
                    out.append(st)
        flush()
        self.steps = out

    def convert_line(self, idx, line):
        codes = line.codes
        block = self.clean_block.get(idx)
        opt = line.opt and block is None
        when_block = [{'k': 'level', 'op': '<', 'n': block}] if block else None
        # coordinates in order of appearance
        positions = []  # (token index, pos)
        for i, t in enumerate(line.t):
            if t[0] == 'tag' and t[1] == 'G':
                p = self.coord(t[2])
                if p:
                    positions.append((i, p))

        def pos_for(i):
            before = [p for j, p in positions if j < i]
            if before:
                return before[-1]
            return positions[0][1] if positions else None

        qtags = [(i, t) for i, t in enumerate(line.t) if t[0] == 'tag' and t[1] in ('QA', 'QT', 'QC')]
        tip = T(line.en, line.ko) if len(bare(line.t)) >= 6 else None

        def step_of(goals, when=None, extra=None):
            s = {}
            if tip:
                s['note'] = tip
            if line.only:
                s['only'] = line.only
            if when:
                s['when'] = when
            if extra:
                s.update(extra)
            s['goals'] = goals
            return s

        if qtags:
            report['lines with quests'] += 1
            accepts, completes, turnins = [], [], []
            for i, t in qtags:
                m = re.match(r'^\s*(\d+)(?:,(\d+))?\s*(.*)$', t[2])
                qid, oi, title = int(m.group(1)), m.group(2), m.group(3).strip()
                pos = pos_for(i)
                if t[1] == 'QA':
                    accepts.append((qid, self.quest_goal('accept', qid, title, line, pos)))
                elif t[1] == 'QT':
                    turnins.append((qid, self.quest_goal('turnin', qid, title, line, pos)))
                else:
                    g = self.objective_goal(qid, int(oi), title, line, pos) if oi else None
                    if g is None:
                        if any(c[0] == qid and c[1]['t'] == 'complete' for c in completes):
                            continue
                        g = self.quest_goal('complete', qid, title, line, pos)
                    completes.append((qid, g))

            # optional or "with the next step": never hold the route
            if (opt or line.oc) and not turnins:
                if completes:
                    self.emit(step_of([g for _, g in completes], extra={'along': True}), holding=False, block=block)
                    report['along steps'] += 1
                first = True
                for qid, g in accepts:
                    g = dict(g, optional=True)
                    if not positions:
                        for k in ('map', 'x', 'y', 'f'):
                            g.pop(k, None)
                    if first and tip:
                        g['note'] = tip
                    first = False
                    self.add_pending(g, line.only, True, block)
                    report['optional goals'] += 1
                return

            emitted = False
            # accepts: one step per level rule
            groups = collections.OrderedDict()
            for qid, g in accepts:
                groups.setdefault(self.gate(qid), []).append(g)
            for n, goals in groups.items():
                when = list(when_block or [])
                if n:
                    when.append({'k': 'level', 'op': '<', 'n': n})
                    report['accept steps with the level rule'] += 1
                self.emit(step_of(goals, when or None), block=block)
                emitted = True
            if completes:
                gates = [self.gate(qid) for qid, _ in completes]
                when = list(when_block or [])
                if all(gates):
                    when.append({'k': 'level', 'op': '<', 'n': max(gates)})
                self.emit(step_of([g for _, g in completes], when or None), block=block)
                emitted = True
            for qid, g in turnins:
                n = self.gate(qid)
                q = db.quest(qid)
                has_work = bool(q and q['objs'])
                if opt or line.oc or block:
                    k = 'complete' if has_work else 'onquest'
                    w = {'k': k, 'q': qid if k == 'complete' else [qid]}
                    self.emit(step_of([g], [w]), block=block)
                    report['turn-ins only when you have it'] += 1
                elif n and has_work:
                    self.emit(step_of([g], [{'k': 'level', 'op': '<', 'n': n}]))
                    self.emit(step_of([dict(g)], [{'k': 'level', 'op': '>=', 'n': n}, {'k': 'complete', 'q': qid}]))
                    report['turn-ins with the level rule'] += 1
                else:
                    self.emit(step_of([g]))
                emitted = True
            return

        # ---- no quest on the line
        f = line.tags('F'); p = line.tags('P'); h = line.tags('H'); s = line.tags('S'); xp = line.tags('XP')
        if xp:
            spec = xp[0][2].split()[0]
            m = re.match(r'^(\d+)(?:([+\-.])(\d+))?$', spec)
            lvl, op, amt = int(m.group(1)), m.group(2), m.group(3)
            g = {'t': 'level', 'level': lvl}
            if op == '-':
                need = db.xp[lvl - 2]
                frac = round(1 - int(amt) / need, 2)
                g = {'t': 'level', 'level': lvl - 1}
                if 0 < frac < 1:
                    g['frac'] = frac
            elif op == '+':
                frac = round(int(amt) / db.xp[lvl - 1], 2)
                if 0 < frac < 1:
                    g['frac'] = frac
            elif op == '.':
                frac = float('0.' + amt)
                if 0 < frac < 1:
                    g['frac'] = frac
            if positions:
                g.update(place(*positions[0][1]))
                g['_w'] = True
                self.here = positions[0][1]
            if line.oc or opt:
                self.emit(step_of([g], when_block, {'along': True}), holding=False, block=block)
                report['along steps'] += 1
            else:
                self.emit(step_of([g], when_block), block=block)
            report['level goals'] += 1
            return
        if s:
            name = s[0][2].strip()
            inn = db.find_inn(name)
            if inn:
                g = {'t': 'sethome', 'location': inn['names'][0], 'area': inn['area'], 'npc': inn['npc'], 'map': inn['map'], 'x': inn['x'], 'y': inn['y']}
                if db.npc_name(inn['npc']):
                    g['npcName'] = db.npc_name(inn['npc'])
                if inn['era']:
                    g['f'] = 'e'
                self.here = (inn['map'], inn['x'], inn['y'])
                self.emit(step_of([g], when_block), block=block)
                report['sethome'] += 1
                return
            report['sethome: unknown inn ' + name] += 1
        if p:
            name = p[0][2].strip()
            node = db.find_taxi(name)
            if node:
                g = {'t': 'getfp', 'location': node['name'].split(',')[0], 'node': node['node']}
                loc = positions[0][1] if positions else (node['map'], node['x'], node['y'])
                g.update(place(*loc)) if positions else g.update({'map': node['map'], 'x': node['x'], 'y': node['y'], 'f': 'e'})
                self.here = loc
                self.emit(step_of([g], when_block), block=block)
                report['getfp'] += 1
                return
            report['getfp: unknown flight point ' + name] += 1
        if f:
            name = f[0][2].strip()
            node = db.find_taxi(name)
            if node:
                g = {'t': 'fly', 'location': node['name'].split(',')[0], 'node': node['node']}
                inn = db.find_inn(name)
                if inn:
                    g['area'] = inn['area']
                self.here = (node['map'], node['x'], node['y'])
                self.cur_map = self.cur_map
                self.emit(step_of([g], when_block), block=block)
                report['fly'] += 1
                return
            report['fly: unknown flight point ' + name] += 1
        if h:
            name = h[0][2].strip()
            inn = db.find_inn(name)
            if inn and not opt:
                self.note(line, block=block)
                self.emit({'goals': [{'t': 'hearth', 'location': inn['names'][0], 'area': inn['area']}], **({'only': line.only} if line.only else {}),
                           **({'when': when_block} if when_block else {})}, holding=False, block=block)
                self.here = (inn['map'], inn['x'], inn['y'])
                report['hearth'] += 1
                return
            report['hearth as a note: ' + name] += 1
        if positions and not opt and not line.tags('T', 'V', 'R'):
            mp, x, y = positions[0][1]
            g = {'t': 'goto', 'r': 20}
            g.update(place(mp, x, y))
            self.here = positions[0][1]
            st = step_of([g], when_block)
            if 'note' not in st and line.en:
                st['note'] = T(line.en, line.ko)
            self.emit(st, block=block)
            report['goto steps'] += 1
            return
        self.note(line, block=block)
        report['notes'] += 1


def finish_goal(g):
    g = {k: v for k, v in g.items() if not k.startswith('_')}
    order = ['t', 'quest', 'title', 'item', 'itemName', 'target', 'npc', 'npcName', 'object', 'objName', 'count', 'oi', 'qlvl',
             'location', 'area', 'node', 'level', 'frac', 'text', 'map', 'x', 'y', 'f', 'r', 'optional', 'only', 'note']
    return {k: g[k] for k in order if k in g} | {k: v for k, v in g.items() if k not in order}


def write(guides):
    os.makedirs(OUT + '/' + FOLDER, exist_ok=True)
    by_min = {}
    for g in guides:
        by_min.setdefault(g.min, g)
    out = ['-- Nood Guide %s for Polestar. Written by its own converter from the Guidelime guide (not by `forge guide compile`).' % VERSION,
           '-- Nood 가이드 %s (Polestar용): Guidelime 가이드에서 자체 변환기로 만든 파일입니다.' % VERSION, '',
           'local KO = GetLocale and GetLocale() == "koKR"',
           'local function T(en, ko) if KO then return ko end return en end', '']
    stats = []
    for g in guides:
        nxt = None
        if g.next:
            m = re.match(r'^(\d+)-', g.next)
            for o in guides:
                if o.races is None and m and o.min == int(m.group(1)):
                    nxt = o
        d = collections.OrderedDict()
        d['id'] = '%s/%s' % (PACK_ID, g.slug)
        d['pack'] = PACK_ID
        d['title'] = g.title
        d['faction'] = 'Horde'
        if g.races:
            d['races'] = g.races
        d['minLevel'], d['maxLevel'] = g.min, g.max
        d['category'] = 'Leveling'
        d['folder'] = T('Nood Guide', 'Nood 가이드')
        if g.desc:
            d['why'] = g.desc
        d['zone'], d['zoneName'] = g.zone, g.zone_name
        if nxt:
            d['next'] = '%s/%s' % (PACK_ID, nxt.slug)
        d['author'] = '씨가 + Claude'
        d['version'] = 1
        out.append('-- Source: %s.lua (BalCon %s)' % (g.stem, SRC_VERSION))
        out.append('Polestar.RegisterGuide((function() return {')
        for k, v in d.items():
            out.append('\t%s = %s,' % (k, lua(v)))
        out.append('\tsteps = {')
        for st in g.steps:
            head = []
            for k in ('title', 'note', 'only', 'when', 'along', 'label'):
                if k in st:
                    head.append('%s = %s' % (k, lua(st[k])))
            out.append('\t\t{ ' + ', '.join(head) + (', ' if head else '') + 'goals = {')
            for goal in st['goals']:
                out.append('\t\t\t' + lua(finish_goal(goal)) + ',')
            out.append('\t\t} },')
        out.append('\t},')
        out.append('} end)())')
        out.append('')
        stats.append((d['id'], len(g.steps), sum(len(s['goals']) for s in g.steps)))
    open('%s/%s/Guides.lua' % (OUT, FOLDER), 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
    return stats


def main():
    guides = []
    for spec in GUIDES:
        g = Guide(*spec)
        g.convert()
        guides.append(g)
    stats = write(guides)
    for s in stats:
        print(s)
    for k, v in sorted(report.items()):
        print('%5d  %s' % (v, k))
    for n in notes_log:
        print('NOTE', n)
    json.dump({'stats': stats, 'report': dict(report)}, open(OUT + '/report.json', 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__' and not os.environ.get('NOOD_GUIDE_ONLY'):
    main()


# ---- the addon's other files ----------------------------------------------------------------------------
def write_addon():
    d = '%s/%s' % (OUT, FOLDER)
    w = lambda name, text: open('%s/%s' % (d, name), 'w', encoding='utf-8', newline='\n').write(text)
    w(FOLDER + '.toc', '''## Interface: 16001
## Title: Polestar Community: Nood Guide - Dungeon Leveling (Forever)
## Title-koKR: Polestar 커뮤니티: Nood 가이드 - 던전 레벨업 (포에버)
## Notes: Dungeon-focused Horde leveling 1-60 for Polestar. Korean or English text, chosen by your game language. Test build %(v)s.
## Notes-koKR: 던전 중심 호드 레벨업 1-60 (Polestar용). 시험판 %(v)s.
## Author: 씨가 + Claude
## Version: %(v)s
## Category: Polestar
## Group: Polestar
## Dependencies: Polestar
## SavedVariables: NoodGuideDB
## X-Polestar-Pack: %(id)s
## X-Polestar-Format: 5
## X-Polestar-Needs: 0.3.0
## X-License: All rights reserved
## X-Curse-Project-ID: 1801649
## X-Website: https://github.com/ebfks1/Nood_Guide_Polstart_Horde_Forever
# Written by its own converter from the BalCon Guidelime guide, following Polestar's docs/PACK_FORMAT.md. Not built by `forge guide compile`.

Pack.lua
MapFrames.lua
Guides.lua
Setup.lua
''' % {'v': VERSION, 'id': PACK_ID})
    w('Pack.lua', '''-- Nood Guide %(v)s for Polestar: the pack's registration (docs/PACK_FORMAT.md, RegisterPack).
local ADDON = ...
local KO = GetLocale and GetLocale() == "koKR"
Polestar.RegisterPack({
	addon = ADDON, id = "%(id)s", format = 5,
	title = KO and "Nood 가이드 - 던전 레벨업 (포에버)" or "Nood Guide - Dungeon Leveling (Forever)",
	author = "씨가 + Claude", version = "%(v)s", license = "All rights reserved",
	website = "https://github.com/ebfks1/Nood_Guide_Polstart_Horde_Forever",
	source = KO and "발컨 Guidelime 가이드 %(sv)s 참고" or "Based on the BalCon Guidelime guide %(sv)s",
	notes = KO and "던전 중심 호드 레벨업 1-60" or "Dungeon-focused Horde leveling 1-60",
})
''' % {'v': VERSION, 'id': PACK_ID, 'sv': SRC_VERSION})
    w('MapFrames.lua', '''-- This pack uses only maps Polestar already has frames for; nothing to add.
Polestar.RegisterMapFrames({ era = {} }, "%s")
''' % PACK_ID)
    w('Setup.lua', open(os.path.dirname(os.path.abspath(__file__)) + '/Setup.lua', encoding='utf-8').read().replace('@VERSION@', VERSION))


if __name__ == '__main__' and not os.environ.get('NOOD_GUIDE_ONLY'):
    write_addon()
