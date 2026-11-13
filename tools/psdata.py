# Reference lookups read from the shipped Polestar 0.3.7 addon data (ids, names, places).
import re, glob, collections, math

P = '/home/claude/polestar'


def _records(path):
    out = {}
    for line in open(path, encoding='utf-8'):
        m = re.match(r'^(\d+)\t(.*)$', line.rstrip('\n'))
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def _unhex(s):
    return re.sub(r'%([0-9A-Fa-f]{2})', lambda m: bytes([int(m.group(1), 16)]).decode('latin-1'), s).encode('latin-1').decode('utf-8', 'replace')


def _decode(payload):
    vals = []
    for f in payload.split(';'):
        if f.startswith("'"):
            t = f[1:]
            vals.append(_unhex(t) if '%' in t else t)
        elif f.startswith('{'):
            vals.append([float(e) if '.' in e else int(e) for e in f[1:].split(',') if e != ''])
        elif f == '':
            vals.append(None)
        else:
            try:
                vals.append(float(f) if '.' in f else int(f))
            except ValueError:
                vals.append(f)
    return vals


class DB:
    def __init__(self):
        self.q = _records(P + '/Polestar_QuestDB/Quests.lua')
        self.n = _records(P + '/Polestar_QuestDB/Npcs.lua')
        self.o = _records(P + '/Polestar_QuestDB/Objects.lua')
        self.i = _records(P + '/Polestar_QuestDB/Items.lua')
        self._cache = {}
        self.era = self._era_maps()
        self.taxi, self.inns = self._travel()
        self.zones = self._zones()
        self.xp = self._xp()

    def _get(self, kind, id):
        key = (kind, id)
        if key not in self._cache:
            raw = getattr(self, kind).get(id)
            self._cache[key] = _decode(raw) if raw is not None else None
        return self._cache[key]

    def quest(self, id):
        r = self._get('q', id)
        if not r:
            return None
        r = r + [None] * (20 - len(r))

        def lst(v):
            if v is None:
                return []
            return v if isinstance(v, list) else [v]
        obj = lst(r[11])
        objs = [(int(obj[k]), int(obj[k + 1]), int(obj[k + 2])) for k in range(0, len(obj) - 2, 3)]
        return dict(title=r[0], level=r[1], min=r[2], start=[int(x) for x in lst(r[6])], finish=[int(x) for x in lst(r[7])],
                    startItem=r[8], objs=objs, zone=r[12])

    def entity(self, ref):
        """ref > 0 npc, < 0 object -> (name, [(map, era, x, y, r)])"""
        r = self._get('n', ref) if ref > 0 else self._get('o', -ref)
        if not r:
            return None
        name = r[0]
        out = []
        i = 1
        while i + 2 < len(r):
            mp, frame, count = r[i], r[i + 1], r[i + 2]
            j = i + 3
            if not isinstance(count, int):
                break
            for _ in range(count):
                if j + 2 >= len(r) + 0 and j + 1 >= len(r):
                    break
                x, y = r[j], r[j + 1]
                rad = r[j + 2] if j + 2 < len(r) else 0
                if x is not None and y is not None:
                    out.append((mp, frame == 0, float(x), float(y), rad or 0))
                j += 3
            i = j
        return name, out

    def item(self, id):
        r = self._get('i', id)
        if not r:
            return None
        name = r[0]
        npcs, objs = [], []
        try:
            i = 1
            cnt = r[i] or 0
            i += 1
            for _ in range(int(cnt)):
                npcs.append((int(r[i]), r[i + 1] or 0))
                i += 2
            cnt = r[i] if i < len(r) and r[i] is not None else 0
            i += 1
            for _ in range(int(cnt)):
                objs.append((int(r[i]), r[i + 1] or 0))
                i += 2
        except (IndexError, TypeError, ValueError):
            pass
        return name, npcs, objs

    def _era_maps(self):
        cnt = collections.defaultdict(lambda: [0, 0])
        for kind in ('n', 'o'):
            for id in getattr(self, kind):
                e = self.entity(id if kind == 'n' else -id)
                if not e:
                    continue
                for mp, era, *_ in e[1]:
                    cnt[mp][0 if era else 1] += 1
        return {mp: (c[0] >= c[1]) for mp, c in cnt.items()}

    def is_era(self, mp):
        return self.era.get(mp, False)

    def _travel(self):
        s = open(P + '/Polestar/Nav/TravelData.lua', encoding='utf-8').read()
        taxi = []
        for m in re.finditer(r'\{(\d+),(\d+),(-?[\d.]+),(-?[\d.]+),(\d+),([\d.]+),([\d.]+),(\d+),"([^"]*)"', s):
            taxi.append(dict(node=int(m.group(1)), map=int(m.group(5)), x=float(m.group(6)), y=float(m.group(7)),
                             faction=int(m.group(8)), name=m.group(9)))
        inns = []
        for m in re.finditer(r'\{area=(\d+),c=\d+,f="(\w)",map=(\d+),names=\{([^}]*)\},npc=(\d+),wx=[-\d.]+,wy=[-\d.]+,x=([\d.]+),y=([\d.]+)\}', s):
            inns.append(dict(area=int(m.group(1)), era=m.group(2) == 'e', map=int(m.group(3)),
                             names=re.findall(r'"([^"]*)"', m.group(4)), npc=int(m.group(5)), x=float(m.group(6)), y=float(m.group(7))))
        return taxi, inns

    def _zones(self):
        z = {}
        for f in glob.glob(P + '/Polestar_Guides*/Guides.lua'):
            s = open(f, encoding='utf-8').read()
            for m in re.finditer(r'zone = (\d+),\s*zoneName = "([^"]*)"', s):
                z.setdefault(m.group(2), int(m.group(1)))
        z.update({'Alterac Mountains': 1416, 'Wetlands': 1437, 'Blasted Lands': 1419, 'Western Plaguelands': 1422,
                  'Loch Modan': 1432, 'Duskwood': 1431, 'Zephras Isle': 2521})
        return z

    def _xp(self):
        s = open(P + '/Polestar/Core/Levels.lua', encoding='utf-8').read()
        m = re.search(r'local LEVEL_XP = \{(.*?)\}', s, re.S)
        return [int(x) for x in re.findall(r'\d+', m.group(1))]

    @staticmethod
    def _norm(name):
        n = name.lower().strip()
        n = re.sub(r'^the ', '', n)
        return n

    def find_taxi(self, name):
        key = self._norm(name)
        best = None
        for t in self.taxi:
            if not (t['faction'] & 2):
                continue
            town = self._norm(t['name'].split(',')[0])
            if town == key:
                return t
            if key.startswith(town) or town.startswith(key):
                best = best or t
        return best

    def find_inn(self, name):
        key = self._norm(name)
        for inn in self.inns:
            for n in inn['names']:
                if self._norm(n) == key:
                    return inn
        return None

    def npc_name(self, id):
        e = self.entity(id)
        return e[0] if e else None


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])
