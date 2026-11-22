# Nood Guide: writes the pack sources (pack.json + .guide files) that Polestar's own compiler builds
# (`forge guide lint`, `forge release pack`), from the same converted route as convert.py.
#   python3 emit_guide.py <out dir> <version>
import os, re, sys, json
os.environ['NOOD_GUIDE_ONLY'] = '1'
import convert as C
from convert import T, db

VERSION = sys.argv[2] if len(sys.argv) > 2 else '1.0.0-beta'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/packs'
WEBSITE = 'https://github.com/ebfks1/Nood_Guide_Polstart_Horde_Forever'
PACKS = {
    'en': dict(id='nood', folder='PolestarPack_Nood', title='Nood Guide - Dungeon Leveling (Forever)', menu='Nood Guide',
               notes='Dungeon-focused Horde leveling 1-60, in English. Based on the BalCon Guidelime guide.',
               source='Based on the BalCon Guidelime guide %s' % C.SRC_VERSION),
    'ko': dict(id='nood-ko', folder='PolestarPack_NoodKorean', title='Nood 가이드 - 던전 레벨업 (포에버, 한국어)', menu='Nood 가이드',
               notes='던전 중심 호드 레벨업 1-60 (한국어). 발컨 Guidelime 가이드를 참고했습니다.',
               source='발컨 Guidelime 가이드 %s 참고' % C.SRC_VERSION),
}
RACE_WORD = {'Scourge': 'Undead'}
OBJ_VERBS = ('kill', 'collect', 'interact')


GUIDE_NAMES = [('12-25 발컨', '12-25 Nood'), ('발컨 12-25', 'Nood 12-25'), ('12-25 BalCon', '12-25 Nood'), ('BalCon 12-25', 'Nood 12-25')]


def txt(v, lang):
    if isinstance(v, T):
        v = (v.ko if (lang == 'ko' and v.ko) else v.en)
    if isinstance(v, str):
        for a, b in GUIDE_NAMES:  # the next guide is called Nood here
            v = v.replace(a, b)
    return v


def plain(s):
    """Text on a line the lexer reads (tip, title, why): no quotes, no comment or note starts, one line."""
    s = re.sub(r'\s*[\r\n]+\s*', ' ', s).replace('"', "'").replace('|', '/')
    s = re.sub(r'(?<!\S)#', '№', s)
    s = re.sub(r'(?<!\S)--(?!\S)', '—', s)
    return s.strip()


def quoted(s):
    s = re.sub(r'\s*[\r\n]+\s*', ' ', s).replace('|', '/').strip()
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def cond(only):
    if not only:
        return None
    names = [c.capitalize() for c in only.get('classes', [])] + [RACE_WORD.get(r, r) for r in only.get('races', [])]
    return ','.join(names)


def num(v):
    return ('%.2f' % v).rstrip('0').rstrip('.')


def at(g):
    return '@%s,%s map %d' % (num(g['x']), num(g['y']), g['map'])


def when_line(w):
    if w['k'] == 'level':
        return 'when level%s%d' % (w['op'], w['n'])
    if w['k'] == 'complete':
        return 'when complete %d' % w['q']
    if w['k'] == 'onquest':
        return 'when onquest %s' % ', '.join(str(x) for x in w['q'])
    raise ValueError(w)


def unknown(kind, id):
    return id in C.UNKNOWN.get(kind, ())


def named(kind, id, name):
    """An id with its name when the data build lacks it."""
    return '%d %s' % (id, quoted(name)) if unknown(kind, id) and name else str(id)


ELITE = set(C.CI.get('elite', []))
NEEDS_WORK = set(C.CI.get('needs_work', []))


def splittable(qid, place):
    """A whole-quest goal is written as one goal per objective only when nothing is lost: every objective has a
    known spawn (else that goal has no place and no arrow), none is elite (a dungeon quest stays one goal), and,
    when the guide wrote a hunting spot, every objective spawns near it (the spot stays the arrow's target)."""
    q = db.quest(qid)
    if not q or not q['objs'] or qid in ELITE:
        return False
    for kind, id, cnt in q['objs']:
        refs = C.objective_refs({'objs': [(kind, id, cnt)]})
        spots = [(mp, x, y) for r in refs for e in [db.entity(r)] if e for mp, era, x, y, rr in e[1]]
        if not spots:
            return False
        if place and not any(mp == place['map'] and C.dist((x, y), (place['x'], place['y'])) <= 3 for mp, x, y in spots):
            return False
    return True


def quest_objectives(qid):
    """One goal per objective, placed by the compiler's data; None when an objective is of a kind with no verb."""
    q = db.quest(qid)
    if not q or not q['objs']:
        return None
    out = []
    for oi, (kind, id, cnt) in enumerate(q['objs'], 1):
        if kind == 1 and db.entity(id):
            out.append('kill %s quest %d.%d' % (named('npc', id, db.entity(id)[0]), qid, C.log_index(qid, oi)))
        elif kind == 2 and db.item(id):
            out.append('collect %s quest %d.%d' % (named('item', id, db.item(id)[0]), qid, C.log_index(qid, oi)))
        elif kind == 3 and db.entity(-id):
            out.append('interact %s quest %d.%d' % (named('object', id, db.entity(-id)[0]), qid, C.log_index(qid, oi)))
        else:
            return None
    return sorted(out, key=lambda x: int(x.rsplit('.', 1)[1]))


def goal_lines(g, lang, along, stats):
    """-> the lines of one goal (most goals: one)."""
    t = g['t']
    tail = ''
    if g.get('optional'):
        tail += ' optional'
    if g.get('only'):
        tail += ' only ' + cond(g['only'])
    note = txt(g.get('note'), lang) if g.get('note') else None
    note = (' -- ' + re.sub(r'\s*[\r\n]+\s*', ' ', note).strip()) if note else ''
    written = g.get('_w') and 'map' in g
    known = (db.quest(g['quest']) is not None and not unknown('quest', g['quest'])) if 'quest' in g else True

    if t in ('accept', 'turnin'):
        s = '%s %d' % (t, g['quest'])
        if not known:
            s += ' ' + quoted(txt(g['title'], lang))
            stats['quests named by the guide'] += 1
        if 'npc' in g and known and not unknown('npc', g['npc']):
            s += ' npc %d' % g['npc']
        elif 'object' in g and known and not unknown('object', g['object']):
            s += ' object %d' % g['object']
        elif 'item' in g and t == 'accept':
            s += ' item %d' % g['item']
        elif 'map' in g:
            s += ' ' + at(g)
            stats['%s: place written in the guide' % t] += 1
        if t == 'accept' and g.get('qlvl') and not known:
            s += ' lvl %d' % g['qlvl']
        return [s + tail + note]
    if t == 'complete':
        # one goal per objective wherever the data allows: Polestar's "While you're here" panel (Dynamic Questing)
        # offers kill/collect/interact goals of later steps when you pass them, never a whole-quest `complete`
        if g['quest'] in NEEDS_WORK:  # an objective the tables miss (a talk, an event): the quest as a whole
            objs = None
        elif written:  # the guide's hunting spot: split only when nothing is lost
            objs = quest_objectives(g['quest']) if known and splittable(g['quest'], g) else None
        else:  # placed by the data, as before
            objs = quest_objectives(g['quest']) if known and 'map' in g else None
        if objs:
            if written:
                stats['complete: one goal per objective, at the guide\'s place'] += 1
                objs = [o + ' ' + at(g) for o in objs]
            else:
                stats['complete: one goal per objective'] += 1
            return [o + tail + (note if i == 0 else '') for i, o in enumerate(objs)]
        s = 'complete %d' % g['quest']
        if not known:
            s += ' ' + quoted(txt(g['title'], lang))
        if 'map' in g and (written or not known):
            s += ' ' + at(g)
            stats['complete: whole quest, at the guide\'s place'] += 1
        else:
            stats['complete: whole quest, no place'] += 1
        return [s + tail + note]
    if t in OBJ_VERBS:
        if not known:
            s = 'complete %d %s' % (g['quest'], quoted(txt(g['title'], lang)))
            if 'map' in g:
                s += ' ' + at(g)
            return [s + tail + note]
        id, kind, name = (g['npc'], 'npc', g['target']) if t == 'kill' else (g['item'], 'item', g['itemName']) if t == 'collect' else (g['object'], 'object', g['objName'])
        s = '%s %s quest %d.%d' % (t, named(kind, id, name), g['quest'], g['oi'])
        if written or (unknown(kind, id) and 'map' in g):
            s += ' ' + at(g)
        return [s + tail + note]
    if t == 'goto':
        return ['goto %s,%s r %d map %d' % (num(g['x']), num(g['y']), g.get('r', 20), g['map']) + tail + note]
    if t == 'level':
        lv = str(g['level']) + ('.%02d' % round(g['frac'] * 100) if g.get('frac') else '')
        out = []
        if written and not along:
            out.append('goto %s,%s r 40 map %d' % (num(g['x']), num(g['y']), g['map']))
        out.append('level ' + lv + tail + note)
        return out
    if t in ('sethome', 'hearth', 'getfp', 'fly'):
        return ['%s %s' % (t, quoted(g['location'])) + tail + note]
    if t == 'note':
        # a ticked-off line: an optional task gets a checkbox in the guide window and never holds the step
        # (BalCon's notes were written to be clicked shut: "확인했으면 눌러 닫기")
        if g.get('hold'):  # a line the player ticks to go on (it holds the step)
            return ['task ' + quoted(txt(g['text'], lang)) + tail]
        return ['task ' + quoted(txt(g['text'], lang)) + ('' if ' optional' in tail else ' optional') + tail]
    raise ValueError(t)


INN_KO = {'Orgrimmar': '오그리마', 'The Crossroads': '크로스로드', 'Undercity': '언더시티', 'Booty Bay': '무법항',
          'Gadgetzan': '가젯잔', 'Razor Hill': '칼바위 언덕', 'Tarren Mill': '타렌 밀농장'}
HEADS_UP_AHEAD = 5  # steps before the hearth


def hearth_notices(g):
    """{step index: [(en, ko)]}: a heads-up a few steps before each Hearthstone step, so the player keeps the stone
    (and its cooldown) for it. It sits in an earlier step, so it is gone by the time the hearth comes."""
    out, last_use = {}, -1
    for h, st in enumerate(g.steps):
        kinds = [x['t'] for x in st['goals']]
        if 'hearth' in kinds:
            loc = next(x['location'] for x in st['goals'] if x['t'] == 'hearth')

            def fits(c, gated_ok):
                if c.get('along') or not c['goals'] or (c.get('when') and not gated_ok):
                    return False
                if c.get('only') and c.get('only') != st.get('only'):
                    return False  # a step for other characters than the hearth's
                return not any(x['t'] in ('hearth', 'fly') for x in c['goals'])
            # the nearest step always shown, up to 12 back; else the nearest one within 5 (a level-rule step:
            # a character far above it skips it, notice and all)
            pick = next((k for k in range(h - 1, max(last_use, h - 13), -1) if fits(g.steps[k], False)), None)
            if pick is None:
                pick = next((k for k in range(h - 1, max(last_use, h - 6), -1) if fits(g.steps[k], True)), None)
            if pick is not None:
                out.setdefault(pick, []).append((
                    '[Heads-up] Soon you hearth to %s. Keep your Hearthstone until then and check its cooldown now.' % loc,
                    '[알림] 곧 귀환석으로 %s에 갑니다. 그때까지 귀환석을 쓰지 말고, 재사용 대기시간이 남았는지 지금 확인하세요.'
                    % INN_KO.get(loc, loc)))
            last_use = h
        elif 'sethome' in kinds:
            last_use = max(last_use, h - 1)
    return out


def guide_text(g, guides, lang, pack, stats):
    nxt = None
    if g.next:
        m = re.match(r'^(\d+)-', g.next)
        for o in guides:
            if o.races is None and m and o.min == int(m.group(1)):
                nxt = o
    L = ['guide %s/%s' % (pack['id'], g.slug),
         'title ' + plain(txt(g.title, lang)),
         'levels %d-%d' % (g.min, g.max),
         'zone map %d' % g.zone,
         'faction Horde']
    if g.races:
        L.append('race ' + ', '.join(RACE_WORD.get(r, r) for r in g.races))
    L.append('folder ' + pack['menu'])
    if g.desc:
        L.append('why ' + plain(txt(g.desc, lang)))
    L.append('coords era')
    if nxt:
        L.append('next %s/%s' % (pack['id'], nxt.slug))
    L.append('# Written by tools/emit_guide.py from %s.lua (BalCon %s). Edit the converter, not this file.' % (g.stem, C.SRC_VERSION))
    heads = hearth_notices(g)
    worked = set()
    for si, st in enumerate(g.steps):
        goals = []
        for goal in st['goals']:
            q = goal.get('quest')
            if goal['t'] in ('complete', 'kill', 'collect', 'interact'):
                worked.add(q)
            elif goal['t'] == 'turnin' and q in NEEDS_WORK and q not in worked:
                # the playtest could not hand it in: no goal worked an objective; do the quest first
                goals.append('complete %d' % q)
                worked.add(q)
                stats['complete added before a hand-in'] += 1
            goals += goal_lines(goal, lang, bool(st.get('along')), stats)
        if not goals:
            continue
        L.append('')
        L.append('step')
        if st.get('only'):
            L.append('  only ' + cond(st['only']))
        for w in st.get('when') or []:
            L.append('  ' + when_line(w))
        if st.get('along'):
            L.append('  along until ' + st['until'] if st.get('until') else '  along')
        if st.get('label'):
            L.append('  label ' + st['label'])
        maps = [x['map'] for x in st['goals'] if 'map' in x]
        if maps:
            L.append('  zone map %d' % maps[0])
        # The step's own description is a ticked-off line too (a `tip` box stays on screen until the step is
        # done, which in a kill or loot step is a long time); a heads-up for a coming hearth comes first.
        for en, ko in heads.get(si, []):
            L.append('  task ' + quoted(ko if lang == 'ko' else en) + ' optional')
            stats['heads-up lines'] += 1
        if st.get('note'):
            L.append('  task ' + quoted(txt(st['note'], lang)) + ' optional')
            stats['step descriptions as tasks'] += 1
        L += ['  ' + x for x in goals]
        stats['steps'] += 1
        stats['goal lines'] += len(goals)
    return '\n'.join(L) + '\n'


LICENSE = '''Nood Guide / Nood 가이드
Copyright (c) 2026 씨가 (ebfks1)

All rights reserved.

The route, the wording and the selection of quests in these guides are the author's own work, based on the
author's BalCon Guidelime guide. You may install and use this addon in the game. Please ask before you
redistribute or republish it.

이 가이드의 동선, 문구, 퀘스트 구성은 제작자의 저작물이며, 제작자의 발컨 Guidelime 가이드를 바탕으로 합니다.
게임에서 자유롭게 설치해 사용할 수 있습니다. 재배포·재게시는 먼저 문의해 주세요.

The names, places and other game facts in the built addon come from Polestar's reference data; the built
addon lists those sources in LICENSE-DATA.txt.
'''


def main():
    import collections
    guides = []
    tabs = [x for x in os.environ.get('NOOD_DUNGEON_TABS', '').split(',') if x]  # test builds: guides whose runs go to tabs
    for spec in C.GUIDES:
        g = C.Guide(*spec)
        g.convert()
        if any(g.stem.startswith(t) for t in tabs):
            import dungeon_tabs
            log = []
            dungeon_tabs.apply(g, log)
            print('\n'.join(log))
        guides.append(g)
    for lang, pack in PACKS.items():
        stats = collections.Counter()
        d = '%s/%s' % (OUT, pack['id'])
        os.makedirs(d + '/guides', exist_ok=True)
        man = dict(id=pack['id'], title=pack['title'], author='씨가', version=VERSION, license='All rights reserved',
                   website=WEBSITE, source=pack['source'], notes=pack['notes'], folder=pack['folder'])
        open(d + '/pack.json', 'w', encoding='utf-8', newline='\n').write(json.dumps(man, ensure_ascii=False, indent='\t') + '\n')
        open(d + '/LICENSE', 'w', encoding='utf-8', newline='\n').write(LICENSE)
        for g in guides:
            open('%s/guides/%s.guide' % (d, g.slug), 'w', encoding='utf-8', newline='\n').write(guide_text(g, guides, lang, pack, stats))
        print(pack['id'], dict(stats))


if __name__ == '__main__':
    main()
