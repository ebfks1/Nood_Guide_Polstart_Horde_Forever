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


def txt(v, lang):
    if isinstance(v, T):
        return (v.ko if (lang == 'ko' and v.ko) else v.en)
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


def quest_objectives(qid):
    """One goal per objective, placed by the compiler's data; None when an objective is of a kind with no verb."""
    q = db.quest(qid)
    if not q or not q['objs']:
        return None
    out = []
    for oi, (kind, id, cnt) in enumerate(q['objs'], 1):
        if kind == 1 and db.entity(id):
            out.append('kill %d quest %d.%d' % (id, qid, oi))
        elif kind == 2 and db.item(id):
            out.append('collect %d quest %d.%d' % (id, qid, oi))
        elif kind == 3 and db.entity(-id):
            out.append('interact %d quest %d.%d' % (id, qid, oi))
        else:
            return None
    return out


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
    known = db.quest(g['quest']) is not None if 'quest' in g else True

    if t in ('accept', 'turnin'):
        s = '%s %d' % (t, g['quest'])
        if not known:
            s += ' ' + quoted(txt(g['title'], lang))
            stats['quests named by the guide'] += 1
        if 'npc' in g and known:
            s += ' npc %d' % g['npc']
        elif 'object' in g and known:
            s += ' object %d' % g['object']
        elif 'item' in g and t == 'accept':
            s += ' item %d' % g['item']
        elif 'map' in g and (written or not known):
            s += ' ' + at(g)
            stats['%s: place written in the guide' % t] += 1
        if t == 'accept' and g.get('qlvl') and not known:
            s += ' lvl %d' % g['qlvl']
        return [s + tail + note]
    if t == 'complete':
        if written or not known:
            s = 'complete %d' % g['quest']
            if not known:
                s += ' ' + quoted(txt(g['title'], lang))
            if 'map' in g:
                s += ' ' + at(g)
            return [s + tail + note]
        objs = quest_objectives(g['quest']) if 'map' in g else None
        if objs:
            stats['complete: one goal per objective'] += 1
            return [o + tail + (note if i == 0 else '') for i, o in enumerate(objs)]
        stats['complete: whole quest, no place'] += 1
        return ['complete %d' % g['quest'] + tail + note]
    if t in OBJ_VERBS:
        id = g['npc'] if t == 'kill' else g['item'] if t == 'collect' else g['object']
        s = '%s %d quest %d.%d' % (t, id, g['quest'], g['oi'])
        if written:
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
        return ['note ' + quoted(txt(g['text'], lang)) + tail]
    raise ValueError(t)


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
    for st in g.steps:
        goals = []
        for goal in st['goals']:
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
            L.append('  along')
        if st.get('note'):
            L.append('  tip ' + plain(txt(st['note'], lang)))
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
    for spec in C.GUIDES:
        g = C.Guide(*spec)
        g.convert()
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
