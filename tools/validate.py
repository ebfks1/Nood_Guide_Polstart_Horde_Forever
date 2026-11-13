# Loads the written addon in Lua 5.1 (the game's Lua) with a stand-in for Polestar's registration calls,
# then checks every guide against the rules of docs/PACK_FORMAT.md / Core/Guides.lua (ported by hand).
import sys, re, collections
from lupa import lua51

D = sys.argv[1]
toc = open(D + '/PolestarPack_Nood.toc', encoding='utf-8').read()
files = [l.strip() for l in toc.split('\n') if l.strip() and not l.startswith('#')]

REQUIRED = {
    'accept': {'quest': 'n', 'title': 's'}, 'turnin': {'quest': 'n', 'title': 's'}, 'complete': {'quest': 'n', 'title': 's'},
    'abandon': {'quest': 'n', 'title': 's'}, 'destroy': {'item': 'n', 'itemName': 's'}, 'kill': {'target': 's'},
    'collect': {'item': 'n', 'itemName': 's'}, 'goto': {'map': 'n', 'x': 'n', 'y': 'n'}, 'talk': {'npc': 'n', 'npcName': 's'},
    'interact': {'object': 'n', 'objName': 's'}, 'use': {'item': 'n', 'itemName': 's'}, 'sethome': {}, 'hearth': {'location': 's'},
    'getfp': {'location': 's'}, 'fly': {'location': 's'}, 'enter': {'location': 's'}, 'train': {}, 'vendor': {},
    'level': {'level': 'n'}, 'task': {'text': 's'}, 'note': {'text': 's'},
}
WHEN_OPS = {'<', '<=', '>', '>='}


def run(locale):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute('''
        captured = { packs = {}, guides = {}, frames = {}, events = {}, prints = {} }
        function GetLocale() return "%s" end
        Polestar = {}
        function Polestar.RegisterPack(m) captured.packs[#captured.packs + 1] = m return true end
        function Polestar.RegisterGuide(g) captured.guides[#captured.guides + 1] = g return true end
        function Polestar.RegisterMapFrames(f, id) captured.frames[#captured.frames + 1] = { f, id } end
        settings = { ["behavior.suggestFrom"] = "guides", ["ui.instance"] = "hide", ["ui.notesOpen"] = false, ["behavior.closeSkipped"] = true }
        function Polestar.Get(p) return settings[p] end
        function Polestar.Set(p, v) settings[p] = v end
        function CreateFrame() local f = {} function f:RegisterEvent(e) captured.events[#captured.events + 1] = e end
            function f:SetScript(_, fn) captured.onevent = fn end return f end
        SlashCmdList = {}
        local real = print
        function print(...) local t = {} for i = 1, select("#", ...) do t[#t + 1] = tostring(select(i, ...)) end captured.prints[#captured.prints + 1] = table.concat(t, " ") end
    ''' % locale)
    for f in files:
        src = open(D + '/' + f, encoding='utf-8').read()
        fn = L.eval('function(src, name) local f, err = loadstring(src, name) if not f then error(err) end return f("PolestarPack_Nood", {}) end')
        fn(src, '@' + f)
    return L


def tolist(t):
    return [t[i] for i in range(1, len(t) + 1)] if t is not None else []


def isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def isstr(v):
    return isinstance(v, str) and v != ''


def check_only(o):
    if o is None:
        return True
    for k in ('classes', 'races', 'factions'):
        if o[k] is not None and not all(isinstance(x, str) for x in tolist(o[k])):
            return False
    return True


def check_when(w):
    if w is None:
        return True
    lst = tolist(w)
    if not lst:
        return False
    for p in lst:
        k = p['k']
        if k == 'level':
            if p['op'] not in WHEN_OPS or not isnum(p['n']):
                return False
        elif k == 'onquest':
            q = tolist(p['q'])
            if not q or not all(isnum(x) for x in q):
                return False
        elif k in ('complete', 'turnedin', 'available'):
            if not isnum(p['q']):
                return False
        else:
            return False
    return True


def check_goal(g):
    t = g['t']
    if t not in REQUIRED:
        return 'unknown verb %s' % t
    for field, kind in sorted(REQUIRED[t].items()):
        v = g[field]
        if not (isnum(v) if kind == 'n' else isstr(v)):
            return '%s needs %s' % (t, field)
    if g['x'] is not None or g['y'] is not None:
        if not (isnum(g['map']) and isnum(g['x']) and isnum(g['y'])):
            return 'coordinates need map, x and y'
        if not (0 <= g['x'] <= 100 and 0 <= g['y'] <= 100):
            return 'coordinates outside 0-100'
    if g['f'] is not None and g['f'] != 'e':
        return 'unknown frame'
    if g['r'] is not None and not (isnum(g['r']) and g['r'] > 0):
        return 'bad radius'
    if g['oi'] is not None and not (isnum(g['oi']) and g['oi'] >= 1):
        return 'bad objective index'
    if g['count'] is not None and not isnum(g['count']):
        return 'bad count'
    if g['text'] is not None and not isinstance(g['text'], str):
        return 'bad text'
    if t == 'level' and g['frac'] is not None and not (isnum(g['frac']) and 0 < g['frac'] < 1):
        return 'bad frac'
    for k in ('level', 'lvl', 'limit'):
        if g[k] is not None and not isnum(g[k]):
            return 'bad ' + k
    if g['qlvl'] is not None and not (isnum(g['qlvl']) or isstr(g['qlvl'])):
        return 'bad qlvl'
    if t == 'sethome' and not isstr(g['location']):
        return 'sethome needs location'
    if not check_only(g['only']):
        return 'bad only'
    for k in ('note',):
        if g[k] is not None and not isinstance(g[k], str):
            return 'bad note'
    if g['optional'] is not None and g['optional'] is not True:
        return 'bad optional'
    return None


def validate(L):
    cap = L.globals().captured
    problems = []
    packs = tolist(cap.packs)
    assert len(packs) == 1, 'one pack'
    p = packs[0]
    if not re.match(r'^[a-z0-9][a-z0-9-]{1,31}$', p['id'] or ''):
        problems.append('pack id')
    for k in ('addon', 'title', 'author', 'version', 'license'):
        if not isstr(p[k]):
            problems.append('pack missing ' + k)
    if p['format'] not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        problems.append('pack format')
    guides = tolist(cap.guides)
    ids = {g['id'] for g in guides}
    stats = []
    for g in guides:
        gid = g['id']
        if not (isstr(gid) and gid.startswith(p['id'] + '/')):
            problems.append('%s: id outside the pack' % gid)
        if g['pack'] != p['id']:
            problems.append('%s: pack' % gid)
        for k in ('title',):
            if not isstr(g[k]):
                problems.append('%s: missing %s' % (gid, k))
        for k in ('minLevel', 'maxLevel'):
            if g[k] is not None and not isnum(g[k]):
                problems.append('%s: bad %s' % (gid, k))
        for k in ('next', 'faction', 'category', 'folder', 'why'):
            if g[k] is not None and not isstr(g[k]):
                problems.append('%s: bad %s' % (gid, k))
        if g['next'] is not None and g['next'] not in ids:
            problems.append('%s: next %s is no guide of the pack' % (gid, g['next']))
        if g['races'] is not None and not all(isstr(x) for x in tolist(g['races'])):
            problems.append('%s: bad races' % gid)
        steps = tolist(g['steps'])
        if not steps:
            problems.append('%s: no steps' % gid)
        c = collections.Counter()
        accepted = set()
        for s, st in enumerate(steps, 1):
            goals = tolist(st['goals'])
            if not goals:
                problems.append('%s step %d: no goals' % (gid, s))
            if not check_only(st['only']):
                problems.append('%s step %d: bad only' % (gid, s))
            if not check_when(st['when']):
                problems.append('%s step %d: bad when' % (gid, s))
            if st['along'] is not None and st['along'] is not True:
                problems.append('%s step %d: bad along' % (gid, s))
            for k in ('title', 'note'):
                if st[k] is not None and not isinstance(st[k], str):
                    problems.append('%s step %d: bad %s' % (gid, s, k))
            holds = False
            for gi, goal in enumerate(goals, 1):
                err = check_goal(goal)
                if err:
                    problems.append('%s step %d goal %d: %s' % (gid, s, gi, err))
                c[goal['t']] += 1
                if goal['t'] != 'note' and not goal['optional']:
                    holds = True
                if goal['t'] == 'accept':
                    accepted.add(goal['quest'])
                for k in ('title', 'text', 'note', 'npcName', 'objName', 'itemName', 'target', 'location'):
                    v = goal[k]
                    if isinstance(v, str) and ('{' in v or '\0' in v):
                        problems.append('%s step %d goal %d: odd character in %s' % (gid, s, gi, k))
            if not holds and not st['along']:
                c['steps that hold nothing'] += 1
                problems.append('%s step %d: nothing holds this step (it would pass unseen)' % (gid, s))
            if st['along']:
                c['along'] += 1
            if st['when'] is not None:
                c['when'] += 1
        stats.append((gid, g['title'], g['minLevel'], g['maxLevel'], g['next'], len(steps), dict(c)))
    return problems, stats, cap


for loc in ('koKR', 'enUS'):
    L = run(loc)
    problems, stats, cap = validate(L)
    print('==', loc, 'files loaded:', len(files), 'guides:', len(stats), 'problems:', len(problems))
    for pr in problems[:40]:
        print('  PROBLEM', pr)
    for s in stats:
        print('  ', s[0], '|', s[1], '|', s[2], '-', s[3], '| next', s[4], '| steps', s[5])
    # the setup file: first login, then again
    L.execute('captured.onevent()')
    L.execute('captured.onevent()')
    print('   setup prints:', len(tolist(cap.prints)), '| settings now:', dict(L.globals().settings.items()))
    for line in tolist(cap.prints):
        print('     ', line)
    L.execute('SlashCmdList["NOODGUIDE"]("undo")')
    print('   after undo:', dict(L.globals().settings.items()))
tot = collections.Counter()
for s in stats:
    tot.update(s[6])
print('goals by verb (all guides):', dict(tot))
