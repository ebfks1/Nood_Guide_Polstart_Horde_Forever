# Test build: a dungeon's run (its steps inside) leaves the leveling guide; in its place one step points to
# Polestar's own dungeon tab (heads-up card -> "Pick up the quests" -> the run -> the hand-in guide).
import re
from convert import T

STAR = re.compile(r'★\s*(.+?)\s+—\s+Lv')
INSIDE_T = ('complete', 'kill', 'collect', 'interact', 'accept', 'turnin')


def text_of(v):
    return (v.en, v.ko) if isinstance(v, T) else (v, v)


def star_names(st):
    """(en, ko) dungeon names from a step's ★ line."""
    texts = []
    if st.get('note'):
        texts.append(text_of(st['note']))
    for g in st['goals']:
        if g['t'] == 'note':
            texts.append(text_of(g['text']))
        elif g.get('note'):
            texts.append(text_of(g['note']))
    for en, ko in texts:
        me, mk = STAR.search(en or ''), STAR.search(ko or '')
        if me or mk:
            return (me.group(1) if me else (mk.group(1) if mk else '')), (mk.group(1) if mk else me.group(1))
    return None


def inside(st):
    if st.get('along') or not st['goals']:
        return False
    work = [g for g in st['goals'] if g['t'] != 'note']
    if not work or any(g['t'] not in INSIDE_T for g in work):
        return False
    return not any(('map' in g) or ('npc' in g) or ('object' in g) or ('item' in g and g['t'] == 'accept' and 'map' in g)
                   for g in work)


EN_NAME = {'성난불길 협곡': 'Ragefire Chasm', '로데론의 폐허': 'Ruins of Lordaeron', '통곡의 동굴': 'Wailing Caverns',
           '그림자송곳니 성채': 'Shadowfang Keep', '검은심연의 나락': 'Blackfathom Deeps',
           '발굴 현장: 저습지': 'Excavation Site: Wetlands', '달라란': 'City of Dalaran', '가시덩굴 우리': 'Razorfen Kraul',
           '붉은십자군 수도원': 'Scarlet Monastery', '울다만': 'Uldaman', '줄파락': "Zul'Farrak", '마라우돈': 'Maraudon',
           '아탈학카르 신전': 'Sunken Temple', '검은바위 나락': 'Blackrock Depths', '검은바위 첨탑 하층': 'Blackrock Spire',
           '검은바위 첨탑': 'Blackrock Spire', '스트라솔름': 'Stratholme', '가시덩굴 구릉': 'Razorfen Downs'}


GONE = set()  # across guides (applied in guide order, per pack): quests picked up only inside a run that went to its tab
LAST = ['']


def apply(g, log):
    if g.stem <= LAST[0]:
        GONE.clear()  # the next pack starts over
    LAST[0] = g.stem
    out, i, steps = [], 0, g.steps
    taken_inside = set()
    pending = None  # (names, index in out) of the last ★ line not yet matched to a run
    while i < len(steps):
        st = steps[i]
        names = star_names(st)
        if names:
            pending = names
        if pending and inside(st):
            j = i
            while j < len(steps) and (inside(steps[j]) or steps[j].get('along')):
                j += 1
            run = steps[i:j]
            kept_along = [s for s in run if s.get('along')]
            quests = sorted({x['quest'] for s in run if not s.get('along') for x in s['goals'] if 'quest' in x})
            en, ko = pending
            ko = re.sub(r'\s*\(.*?\)\s*$', '', ko).strip()  # "검은바위 나락 (1차)" -> the dungeon's own name
            en = EN_NAME.get(ko, re.sub(r'\s*\(.*?\)\s*$', '', en).strip())
            if not re.match(r'[A-Za-z]', en):
                raise SystemExit('dungeon_tabs: no English name for %s' % ko)
            out.extend(kept_along)  # along steps first: they run "until" the run, whose label goes to the tab step
            out.append({'goals': [
                {'t': 'note', 'hold': True, 'text': T(
                    '[Dungeon] %s: on the Polestar dungeon card press "Pick up the quests" (no card: /polestar dungeontoast %s). '
                    'Tick this when the run and hand-ins in that tab are done.' % (en, en),
                    '[던전] %s: Polestar 던전 알림 카드에서 "퀘스트 수집"을 누르세요 (카드가 없으면 /polestar dungeontoast %s). '
                    '새 탭에서 던전·제출을 마치면 체크하세요.' % (ko, en))},
            ], '_holds': True, '_block': None, '_gated': False,
                'label': next((s['label'] for s in run if not s.get('along') and s.get('label')), None)})
            taken_inside.update(x['quest'] for s2 in run if not s2.get('along') for x in s2['goals'] if x['t'] == 'accept')
            log.append('%s: %s run (%d steps, quests %s) -> dungeon tab step' % (g.stem, en, len(run) - len(kept_along), quests))
            pending = None
            i = j
            continue
        out.append(st)
        i += 1
    # quests picked up only inside a run that went to its tab: their later goals go too (the hand-in guide has them)
    outside = {x['quest'] for st in out for x in st['goals'] if x['t'] == 'accept'}
    gone = (taken_inside | GONE) - outside
    GONE.update(gone)
    final = []
    for st in out:
        if gone and any(x.get('quest') in gone for x in st['goals']):
            st = dict(st, goals=[x for x in st['goals'] if x.get('quest') not in gone])
            if not [x for x in st['goals'] if x['t'] != 'note']:
                log.append('%s: dropped a step of %s (picked up inside a run)' % (g.stem, sorted(gone)))
                continue
        final.append(st)
    g.steps = final
