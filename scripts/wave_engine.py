"""Волна SRD 2014 после восстановления группы; фиксированные политики.

Действия, реакции, Щит, лечение, смерть, концентрация Талиса, метамагия
и геометрия сетки переиспользуются из неизменённого vordt_engine.
"""
from dataclasses import dataclass, field, asdict
from functools import lru_cache
import math
import random
import re

from bestiary_report import load, save_bonus
from vordt_engine import Battle, Config, Web, distance

WAVES = {
    'orcs': [('orc', 8)],
    'ghouls': [('ghoul', 6)],
    'mixed': [('bugbear', 4), ('veteran', 1)],
    'skeletons': [('skeleton', 12)],
}
WAVE_NAMES = {'orcs': '8 орков, опасность ½', 'ghouls': '6 упырей, опасность 1',
              'mixed': '4 багбира, опасность 1, и ветеран, опасность 3',
              'skeletons': '12 скелетов-лучников, опасность ¼'}
TACTICS = ('web', 'heightened', 'careful', 'whip', 'orb')


@dataclass(frozen=True)
class Supplies:
    p3: int = 2
    p2: int = 1
    p1: int = 6
    enhanced: bool = True
    oil: int = 4
    balls: bool = True
    temp_hp: int = 0

    def __post_init__(self):
        for key, maximum in [('p3', 2), ('p2', 1), ('p1', 6), ('oil', 4), ('temp_hp', 8)]:
            value = getattr(self, key)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum:
                raise ValueError(f'{key}: целое от 0 до {maximum}')
        if self.enhanced and not self.p1:
            raise ValueError('Улучшенное 1.1 требует хотя бы одну дозу 1.1')
        if not all(isinstance(getattr(self, key), bool) for key in ('enhanced', 'balls')):
            raise ValueError('enhanced и balls: логические значения')


PRESETS = {
    'intact': Supplies(),
    'no_33': Supplies(p3=0),
    'drunk_all': Supplies(p3=0, p2=0, p1=0, enhanced=False),
    'no_tools': Supplies(oil=0, balls=False),
}


@dataclass(frozen=True)
class WaveConfig:
    wave: tuple = (('orc', 8),)
    terrain: str = 'corridor'
    tactic: str = 'careful'
    supplies: Supplies = field(default_factory=Supplies)
    start: int = 40
    max_rounds: int = 40
    cautious_balls: bool = True
    tools: bool = True

    def __post_init__(self):
        if self.terrain not in ('field', 'corridor') or self.tactic not in TACTICS:
            raise ValueError('Неизвестная местность или тактика')
        if self.start < 20 or self.start > 75 or self.start % 5 or self.max_rounds <= 0:
            raise ValueError('Старт: 20–75 фт, кратно 5; лимит раундов положительный')
        if not self.wave or sum(n for _, n in self.wave) > 24:
            raise ValueError('От 1 до 24 врагов')
        for index, n in self.wave:
            if index not in monster_data() or not isinstance(n, int) or isinstance(n, bool) or n <= 0:
                raise ValueError('Неизвестный враг или неверное количество')


@lru_cache(None)
def monster_data():
    # Только полностью реализованные блоки; произвольная поддержка неизвестных
    # способностей не подразумевается. Сам состав и количества настраиваются.
    return {m['index']: m for m in load() if m['index'] in ('orc', 'ghoul', 'bugbear', 'veteran', 'skeleton')}


@dataclass
class Enemy:
    name: str
    data: dict
    hp: int
    pos: tuple
    restrained: bool = False
    prone: bool = False
    reaction: bool = True
    whipped: bool = False
    oil: bool = False
    oil_until: int = 0
    speed_penalty: bool = False
    movement: int = 30

    @property
    def up(self):
        return self.hp > 0

    @property
    def dead(self):
        return not self.up

    @property
    def ac(self):
        return self.data['armor_class'][0]['value']

    @property
    def index(self):
        return self.data['index']

    def save(self, ability):
        return save_bonus(self.data, ability)


class WaveBattle(Battle):
    def __init__(self, config=None, rng=None, record=False):
        self.wave_config = config or WaveConfig()
        super().__init__(Config(potions=False, precreated_slot=False,
                                max_rounds=self.wave_config.max_rounds), 'урон', rng, record)
        # После Вордта восстанавливаются ресурсы; Доспехи мага ещё действуют.
        self.L.slots[1] = 4
        self.enemies = []
        self.paralyzed = {p.name: 0 for p in self.pcs}
        self.pc_restrained = set()
        self.dragon = False
        self.dragon_until = 0
        self.heightened_target = None
        self.balls_zone = None
        self.balls_left = self.wave_config.supplies.balls
        self.oil_left = self.wave_config.supplies.oil
        self.used = dict(p3=0, p2=0, p1=0, enhanced=0, oil=0, balls=0)
        self.web_casts = 0
        self.whip_casts = 0
        self.first_fall_round = None
        s = self.wave_config.supplies
        self.T.temp_hp = s.temp_hp
        self.potions = [3] * s.p3 + [2] * s.p2
        self.small_potions = [True] * int(s.enhanced) + [False] * (s.p1 - int(s.enhanced))
        if self.wave_config.terrain == 'corridor':
            self.F.pos, self.T.pos, self.L.pos = (0, 0), (-10, 0), (-10, 5)
        else:
            self.F.pos, self.T.pos, self.L.pos = (0, 0), (-10, -10), (-10, 10)
        for index, count in self.wave_config.wave:
            data = monster_data()[index]
            for _ in range(count):
                i = len(self.enemies)
                pos = ((self.wave_config.start + 5 * (i // 2), 5 * (i % 2))
                       if self.wave_config.terrain == 'corridor' else
                       (self.wave_config.start + 5 * (i // 4), -15 + 10 * (i % 4)))
                self.enemies.append(Enemy(f'{index}-{i+1}', data, data['hit_points'], pos))
        self.order = sorted([(self.d20() + p.initiative, p.name) for p in self.pcs] +
                            [(self.d20() + m.save('dex'), m.name) for m in self.enemies], key=lambda v: -v[0])
        self.by_name = {a.name: a for a in self.pcs + self.enemies}
        self.events = []  # удалить setup босса: далее только состояние волны
        self.emit('wave_setup', config=asdict(self.wave_config), positions={a.name: a.pos for a in self.pcs + self.enemies},
                  slots={p.name: dict(p.slots) for p in self.pcs}, temp_hp=self.T.temp_hp)

    def awake(self, p):
        return p.up and not self.paralyzed[p.name]

    def can_react_spell(self, p):
        return self.awake(p) and super().can_react_spell(p)

    def stop_web(self, reason):
        super().stop_web(reason)
        for m in getattr(self, 'enemies', []):
            m.restrained = False
        if hasattr(self, 'pc_restrained'):
            self.pc_restrained.clear()

    def hurt(self, p, amount, damage_type, critical=False):
        before = self.falls
        received = amount // 2 if damage_type in p.resistance else amount
        super().hurt(p, amount, damage_type, critical)
        if self.falls > before and self.first_fall_round is None:
            self.first_fall_round = self.round
        if p is self.L and self.dragon and received > 0:
            if not self.awake(p):
                self.dragon = False
            elif self.d20() + p.saves['con'] + (4 if p.song else 0) < max(10, received // 2):
                self.dragon = False
                self.emit('dragon_ended', reason='damage')

    def in_bounds(self, pos):
        return -30 <= pos[0] <= 120 and (pos[1] in (0, 5) if self.wave_config.terrain == 'corridor' else -30 <= pos[1] <= 30)

    def nearby(self, p):
        return any(m.up and distance(p.pos, m.pos) <= 5 for m in self.enemies)

    def route(self, actor, goal, budget, stop=5, slow=False):
        """Жадный путь как в модели Вордта; проход сквозь союзника стоит 10 фт.

        Нельзя пройти сквозь врага или закончить движение в занятой клетке.
        В поле предпочитает обход зоны, когда он не удлиняет путь.
        """
        if isinstance(actor, Enemy) and actor.restrained or actor.name in self.pc_restrained:
            return []
        others = [a for a in self.pcs + self.enemies if a is not actor and not a.dead]
        friends = {a.pos for a in others if isinstance(a, Enemy) == isinstance(actor, Enemy)}
        foes = {a.pos for a in others if isinstance(a, Enemy) != isinstance(actor, Enemy)}
        pos, spent, path = actor.pos, 0, []
        immune = self.web and actor.name in self.web.immune
        for _ in range(30):
            if distance(pos, goal) <= stop and pos not in friends:
                break
            candidates = [(pos[0]+dx, pos[1]+dy) for dx in (-5, 0, 5) for dy in (-5, 0, 5) if dx or dy]
            candidates = [q for q in candidates if self.in_bounds(q) and q not in foes and
                          (distance(q, goal) < distance(pos, goal) or
                           distance(q, goal) == distance(pos, goal) and q not in [v[0] for v in path])]
            if not candidates:
                break
            cost = lambda q: 5 * (1 + int(q in friends) + int(bool(self.active_web(q) and not immune))) * (2 if slow else 1)
            q = min(candidates, key=lambda q: (distance(q, goal), cost(q), q in friends,
                                              abs(q[0]-goal[0])+abs(q[1]-goal[1])))
            if spent + cost(q) > budget:
                break
            spent += cost(q)
            path.append((q, spent))
            pos = q
        while path and path[-1][0] in friends:
            path.pop()
        return path

    def move(self, actor, goal, stop=5, slow=False):
        spent = 0
        for pos, total in self.route(actor, goal, actor.movement, stop, slow):
            if not actor.up or isinstance(actor, Enemy) and actor.restrained or actor.name in self.pc_restrained:
                break
            old = actor.pos
            if isinstance(actor, Enemy):
                if self.awake(self.F) and self.F.reaction and distance(old, self.F.pos) <= 5 < distance(pos, self.F.pos):
                    self.F.reaction = False
                    self.weapon(self.F, actor, opportunity=True)
            else:
                for m in self.enemies:
                    if m.up and m.reaction and distance(old, m.pos) <= 5 < distance(pos, m.pos):
                        m.reaction = False
                        self.enemy_attack(m, actor, opportunity=True)
                        if not actor.up:
                            break
            if not actor.up or not isinstance(actor, Enemy) and not self.awake(actor):
                break
            actor.pos = pos
            spent = total
            self.emit('move', target=actor.name, start=old, end=pos)
            if self.active_web(pos) and not self.active_web(old):
                self.zone_save(actor, 'entry')
            if self.balls_zone and Web(self.balls_zone).contains(pos) and not Web(self.balls_zone).contains(old) and not slow:
                face = self.d20()
                bonus = actor.save('dex') if isinstance(actor, Enemy) else actor.saves['dex']
                if face + bonus < 10:
                    actor.prone = True
                self.emit('balls_save', target=actor.name, face=face, prone=actor.prone)
                if actor.prone:
                    # Отложенное вставание не бесплатно: остаток хода не движется.
                    break
        actor.movement = max(0, actor.movement - spent)

    def zone_save(self, actor, source):
        if not self.active_web(actor.pos) or actor.name in self.web.immune:
            return
        enemy = isinstance(actor, Enemy)
        restrained = actor.restrained if enemy else actor.name in self.pc_restrained
        height = actor.name == self.heightened_target and self.web.heightened_pending
        if height:
            self.web.heightened_pending = False
        face = self.d20(advantage=(not enemy and getattr(self, 'dodging', None) == actor.name and not restrained),
                        disadvantage=restrained or height)
        bonus = actor.save('dex') if enemy else actor.saves['dex']
        if face + bonus < 14:
            if enemy:
                actor.restrained = True
            else:
                self.pc_restrained.add(actor.name)
            actor.movement = 0
        self.emit('web_save', target=actor.name, source=source, face=face, restrained=(actor.restrained if enemy else actor.name in self.pc_restrained))

    def cast_wave_web(self):
        live = [m for m in self.enemies if m.up and distance(self.T.pos, m.pos) <= 60]
        if not live or not self.cast(self.T, 'Паутина', 2):
            return False
        self.stop_web('new_concentration')
        near = min(live, key=lambda m: distance(m.pos, self.F.pos))
        if self.wave_config.terrain == 'corridor':
            bounds = (0 if self.wave_config.tactic == 'careful' else 5, -5,
                      20 if self.wave_config.tactic == 'careful' else 25, 15)
        else:
            placements = [(m.pos[0]-10, m.pos[1]-10, m.pos[0]+10, m.pos[1]+10) for m in live]
            bounds = max(placements, key=lambda b: (sum(Web(b).contains(m.pos) for m in live),
                                                    -sum(Web(b).contains(p.pos) for p in self.pcs)))
        immune, heightened = set(), False
        if self.wave_config.tactic == 'careful':
            if self.T.careful_free:
                self.T.careful_free = False
            else:
                self.spend_meta(1)
            immune = {p.name for p in self.pcs}
        elif self.wave_config.tactic == 'heightened':
            heightened = self.spend_meta(3)
        self.heightened_target = near.name if heightened else None
        self.web = Web(bounds, heightened_pending=heightened, immune=immune)
        self.web_casts += 1
        self.emit('web_created', bounds=bounds, immune=sorted(immune), heightened_target=self.heightened_target)
        return True

    def damage_enemy(self, m, amount, kind, critical=False):
        if not m.up:
            return
        if kind in m.data['damage_immunities']:
            amount = 0
        elif kind in m.data['damage_resistances']:
            amount //= 2
        elif kind in m.data['damage_vulnerabilities']:
            amount *= 2
        if kind == 'fire' and m.oil and self.clock < m.oil_until and amount:
            amount += 5
            m.oil = False
            self.emit('oil_ignited', target=m.name, bonus=5)
        m.hp = max(0, m.hp - amount)
        self.emit('enemy_damage', target=m.name, amount=amount, kind=kind, hp=m.hp, critical=critical)
        if kind == 'fire' and self.active_web(m.pos):
            self.web.fires.setdefault(self.web.cell(m.pos), self.clock + len(self.order))

    def weapon(self, p, m, opportunity=False):
        if not self.awake(p) or not m.up or distance(p.pos, m.pos) > 5:
            return False
        face = self.d20(advantage=m.restrained or m.prone,
                        disadvantage=p.prone or p.name in self.pc_restrained)
        hit = face != 1 and (face == 20 or face + 6 >= m.ac)
        if hit:
            mult = 2 if face == 20 else 1
            self.damage_enemy(m, self.roll(2 * mult, 6)+4, 'slashing')
            if p.slots[1] > 1:
                p.slots[1] -= 1
                self.damage_enemy(m, self.roll((3 if m.data['type'] == 'undead' else 2) * mult, 8), 'radiant')
        self.emit('weapon_attack', target=p.name, enemy=m.name, hit=hit, opportunity=opportunity)
        return True

    def attack_spell(self, p, m, level=0):
        if not m.up or distance(p.pos, m.pos) > (90 if level else 120):
            return False
        kind = ('fire' if m.oil and not self.active_web(m.pos) else 'acid') if level else (
            'fire' if p is self.L and not self.active_web(m.pos) else 'cold' if p is self.T else 'necrotic')
        spell = 'Хроматический шар' if level else 'Огненный снаряд' if kind == 'fire' else 'Луч холода' if kind == 'cold' else 'Леденящее прикосновение'
        if not self.cast(p, spell, level):
            return False
        dist = distance(p.pos, m.pos)
        face = self.d20(advantage=m.restrained or m.prone and dist <= 5,
                        disadvantage=p.prone or p.name in self.pc_restrained or self.nearby(p) or m.prone and dist > 5)
        if face != 1 and (face == 20 or face + (6 if p is self.T else 6) >= m.ac):
            self.damage_enemy(m, self.roll((level+2 if level else 1)*(2 if face == 20 else 1), 8 if level else 10 if kind == 'fire' else 8), kind)
            if kind == 'cold':
                m.speed_penalty = True
        self.emit('spell_attack', target=p.name, enemy=m.name, spell=spell, face=face)
        return True

    def whip(self):
        targets = sorted([m for m in self.enemies if m.up and distance(m.pos, self.T.pos) <= 90],
                         key=lambda m: (distance(m.pos, self.F.pos), -m.hp))[:2]
        if not targets or not self.cast(self.T, 'Плеть Таши', 2):
            return False
        if len(targets) == 2 and not self.spend_meta(2):
            targets = targets[:1]
        amount = self.roll(3, 6)
        for m in targets:
            failed = self.d20() + m.save('int') < 14
            self.damage_enemy(m, amount if failed else amount // 2, 'psychic')
            if failed:
                m.whipped, m.reaction = True, False
        self.whip_casts += 1
        return True

    def cone(self, origin):
        live = [m for m in self.enemies if m.up]
        angles = [math.atan2(m.pos[1]-origin[1], m.pos[0]-origin[0]) for m in live if m.pos != origin]
        aims = angles + [a + ((b-a+math.pi) % (2*math.pi)-math.pi)/2 for i, a in enumerate(angles) for b in angles[i+1:]]
        best, score = [], (0, 0, -99)
        for angle in aims:
            ux, uy = math.cos(angle), math.sin(angle)
            hits = []
            for a in live + [p for p in self.pcs if not p.dead and p.pos != origin]:
                x, y = a.pos[0]-origin[0], a.pos[1]-origin[1]
                f, side = x*ux+y*uy, abs(x*uy-y*ux)
                if 0 < f <= 15+1e-8 and side <= f/2+1e-8:
                    hits.append(a)
            value = (sum(isinstance(a, Enemy) for a in hits),
                     sum(isinstance(a, Enemy) and a.restrained for a in hits),
                     -sum(not isinstance(a, Enemy) for a in hits))
            if value > score:
                score, best = value, hits
        return best

    def dragon_action(self):
        hits = self.cone(self.L.pos)
        if sum(isinstance(a, Enemy) for a in hits) < 2 or any(not isinstance(a, Enemy) for a in hits):
            return False
        self.L.action = False
        amount = self.roll(3, 6)
        self.emit('dragon_breath', targets=[a.name for a in hits], raw_damage=amount)
        for m in hits:
            failed = self.d20(disadvantage=m.restrained) + m.save('dex') < 14
            self.damage_enemy(m, amount if failed else amount // 2, 'cold')
        return True

    def use_potion(self):
        p = self.T
        if not self.awake(p) or not p.bonus or p.hp > 14:
            return False
        if self.potions:
            level = self.potions.pop(0)
            amount = self.roll(4, 4)-1 if level == 3 else self.roll(2, 4)+1
            self.used['p3' if level == 3 else 'p2'] += 1
        elif self.small_potions:
            enhanced = self.small_potions.pop(0)
            amount = self.roll(1, 4) + (2 if enhanced else 0)
            self.used['p1'] += 1
            self.used['enhanced'] += int(enhanced)
        else:
            return False
        p.bonus = False
        self.heal(p, amount, 'зелье')
        self.emit('bonus_action', target=p.name, action='potion', amount=amount)
        return True

    def use_tools(self, target):
        p = self.T
        if not self.wave_config.tools or not p.action:
            return False
        # В приоритете контроль магией; шарики — следующий свободный ход.
        if self.balls_left and self.round <= 3 and self.wave_config.terrain == 'corridor' and target.pos[0] >= 10:
            p.action = False
            self.balls_left = False
            self.move(p, (0, 5), stop=0)
            if p.pos != (0, 5) or not self.awake(p):
                self.balls_left = True
                self.balls_zone = None
                return True  # действие в политике зарезервировано, не второй ход
            self.balls_zone = (5, 0, 15, 10)
            self.used['balls'] += 1
            self.emit('balls_deployed', bounds=self.balls_zone)
            return True
        # Масло полезно как подготовка огненного заговора Лаэля, когда ячеек на урон нет.
        if (self.oil_left and not self.offensive_slot(p) and not self.offensive_slot(self.L) and self.awake(self.L)
                and distance(p.pos, target.pos) <= 20 and not self.active_web(target.pos) and not target.oil):
            p.action = False
            self.oil_left -= 1
            self.used['oil'] += 1
            face = self.d20(disadvantage=self.nearby(p) or p.prone or target.prone)
            if face != 1 and (face == 20 or face+2 >= target.ac):
                target.oil = True
                target.oil_until = self.clock + 10*len(self.order)
            self.emit('oil_throw', target=target.name, face=face, hit=target.oil)
            return True
        return False

    def pc_turn(self, p):
        was_prone = p.prone
        super().begin_pc_turn(p)
        if p.name in self.pc_restrained or self.paralyzed[p.name]:
            p.prone = was_prone
            p.movement = 0
        if not self.awake(p):
            p.action = p.bonus = p.reaction = False
            return
        if self.active_web(p.pos):
            self.zone_save(p, 'start_of_turn')
        if p.name in self.pc_restrained:
            p.action = False
            if self.d20()+p.saves['str'] >= 14:
                self.pc_restrained.remove(p.name)
                # Расход на вставание уже учитывался; освобождение его не возвращает.
                p.movement = max(0, p.speed - (p.speed//2 if was_prone else 0))
            return
        live = [m for m in self.enemies if m.up]
        if not live:
            return
        target = min(live, key=lambda m: (distance(p.pos, m.pos), m.hp))
        if p is self.F:
            down = [q for q in self.pcs if not q.dead and not q.up]
            if down and (p.loh or p.slots[1]):
                q = min(down, key=lambda q: distance(q.pos, p.pos))
                self.move(p, q.pos)
                if self.awake(p) and distance(p.pos, q.pos) <= 5:
                    if p.loh:
                        amount = min(10, p.loh)
                        p.loh -= amount
                        p.action = False
                        self.heal(q, amount, 'Возложение рук')
                    elif self.cast(p, 'Лечение ран', 1):
                        self.heal(q, self.roll(1, 8)+3, 'Лечение ран')
                    return
            # Держит вход; в поле сближается, в проходе не уходит глубже 5 фт.
            if self.wave_config.terrain == 'field' or target.pos[0] <= 10:
                self.move(p, target.pos)
            if self.awake(p) and distance(p.pos, target.pos) <= 5:
                p.action = False
                self.weapon(p, target)
            else:
                p.action = False  # Уклонение, если враг ещё не подошёл
                self.dodging = p.name
                self.emit('dodge', target=p.name)
            return
        if p is self.T:
            self.use_potion()
            if self.wave_config.tactic in ('web', 'heightened', 'careful') and self.web_casts == 0 and p.slots[2]:
                self.cast_wave_web()
                return
            if self.use_tools(target):
                return
            if self.wave_config.tactic == 'whip' and p.slots[2]:
                self.whip()
                return
            lv = self.offensive_slot(p)
            self.attack_spell(p, target, lv)
        else:
            if not p.song and p.song_uses and p.bonus:
                p.bonus = False
                p.song, p.song_until = True, self.clock+10*len(self.order)
                p.song_uses -= 1
                p.movement += 10
            # Дыхание на себя после Песни, пока есть Паутина и минимум две цели.
            if self.wave_config.tactic in ('web', 'heightened', 'careful') and not self.dragon and p.bonus and p.slots[2] and self.web and self.web.concentrating:
                if self.cast(p, 'Дыхание дракона', 2, 'bonus'):
                    self.dragon, self.dragon_until = True, self.clock+10*len(self.order)
            if self.dragon:
                if distance(p.pos, target.pos) > 15:
                    self.move(p, target.pos, stop=10)
                if self.awake(p) and self.dragon_action():
                    return
            lv = 0 if p.bonus_spell else self.offensive_slot(p)
            if lv and distance(p.pos, target.pos) <= 120 and self.cast(p, 'Волшебные стрелы', lv):
                # Цели назначаются до урона: нет переноса стрелы после убийства.
                targets = sorted([m for m in live if m.up and distance(p.pos, m.pos) <= 120], key=lambda m: m.hp)
                allocation, remaining = [], lv+2
                for m in targets:
                    n = min(remaining, max(1, math.ceil(m.hp/3.5)))
                    allocation.append((m, n))
                    remaining -= n
                    if not remaining:
                        break
                if remaining:
                    allocation.append((targets[-1], remaining))
                dart = self.roll(1, 4)+1
                for m, n in allocation:
                    self.damage_enemy(m, dart*n, 'force')
            elif not lv:
                oily = [m for m in live if m.oil and not self.active_web(m.pos)]
                self.attack_spell(p, min(oily, key=lambda m: m.hp) if oily else target)

    def enemy_attack(self, m, p, opportunity=False, ranged=False, attack=None):
        if not m.up or p.dead:
            return False
        if attack is None:
            name = ('Shortbow' if ranged else 'Shortsword') if m.index == 'skeleton' else 'Claws' if m.index == 'ghoul' else 'Javelin' if ranged else 'Morningstar' if m.index == 'bugbear' else 'Longsword' if m.index == 'veteran' else 'Greataxe'
            attack = next(a for a in m.data['actions'] if a['name'] == name)
        if not ranged and distance(m.pos, p.pos) > 5:
            return False
        dist = distance(m.pos, p.pos)
        normal, long = (80, 320) if m.index == 'skeleton' else (30, 120)
        if ranged and dist > long:
            return False
        paralyzed = bool(self.paralyzed[p.name])
        face = self.d20(advantage=paralyzed or not p.up or p.name in self.pc_restrained or p.prone and not ranged,
                        disadvantage=m.restrained or m.prone or (getattr(self, 'dodging', None) == p.name and self.awake(p) and p.name not in self.pc_restrained) or ranged and (p.prone or dist > normal or self.nearby_enemy(m)))
        total, critical = face + attack['attack_bonus'], face == 20
        hit = face != 1 and (critical or total >= p.armor)
        if hit and self.shield(p, total, critical):
            hit = False
        if hit:
            critical = critical or (paralyzed or not p.up) and dist <= 5
            damage = attack['damage'][0]
            if 'from' in damage:
                damage = damage['from']['options'][0]
            dice = damage['damage_dice']
            if ranged and m.index == 'bugbear':
                dice = '1d6+2'  # Brute включён только в ближний вариант
            n, sides, add = map(int, re.fullmatch(r'(\d+)d(\d+)\+(\d+)', dice).groups())
            self.hurt(p, self.roll(n*(2 if critical else 1), sides)+add, damage['damage_type']['index'], critical)
            if m.index == 'ghoul' and p is not self.L and p.up and self.d20()+p.saves['con'] < 10:
                self.paralyzed[p.name] = self.clock + 10*len(self.order)
                p.reaction = False
                if p is self.T:
                    self.stop_web('paralyzed')
                if p.song:
                    p.song = False
                self.emit('paralyzed', target=p.name)
        self.emit('enemy_attack', enemy=m.name, target=p.name, hit=hit, face=face, critical=critical, ranged=ranged, opportunity=opportunity)
        return hit

    def nearby_enemy(self, m):
        return any(self.awake(p) and distance(m.pos, p.pos) <= 5 for p in self.pcs)

    def enemy_turn(self, m):
        m.reaction = not m.whipped
        speed = 30 - (10 if m.speed_penalty else 0)
        m.movement = speed
        m.speed_penalty = False
        if m.prone and not m.restrained:
            m.movement -= speed//2
            m.prone = False
        if self.active_web(m.pos):
            self.zone_save(m, 'start_of_turn')
        targets = [p for p in self.pcs if p.up] or [p for p in self.pcs if not p.dead]
        if not targets:
            return
        p = min(targets, key=lambda p: (distance(m.pos, p.pos), p.hp))
        ranged = m.index == 'skeleton'
        action_used = False
        if m.restrained and not ranged and distance(m.pos, p.pos) > 5:
            action_used = True
            if self.d20()+m.save('str') >= 14:
                m.restrained = False
                m.movement = speed
                if m.prone:
                    m.movement -= speed//2
                    m.prone = False
        if not m.restrained:
            allowed_move = not m.whipped or not action_used and not ranged and distance(m.pos, p.pos) > 5
            if allowed_move:
                if m.index == 'orc' and not m.whipped:
                    m.movement += 30  # Aggressive, бонусное движение к врагу
                slow = bool(self.balls_zone and self.wave_config.cautious_balls and
                            any(Web(self.balls_zone).contains(q) for q, _ in
                                self.route(m, p.pos, m.movement, 5 if not ranged else 60)))
                if not ranged or distance(m.pos, p.pos) > 80:
                    self.move(m, p.pos, stop=5 if not ranged else 60, slow=slow)
                if m.whipped:
                    action_used = True
        if not m.up:
            return
        if not action_used:
            close = [q for q in targets if distance(m.pos, q.pos) <= 5]
            p = min(close, key=lambda q: q.hp) if close else p
            use_ranged = ranged and not close or m.index in ('orc', 'bugbear') and not close
            if m.index == 'veteran' and close:
                for name in ('Longsword', 'Longsword', 'Shortsword'):
                    if not p.up:
                        eligible = [q for q in targets if q.up and distance(m.pos, q.pos) <= 5]
                        if eligible:
                            p = min(eligible, key=lambda q: q.hp)
                    self.enemy_attack(m, p, attack=next(a for a in m.data['actions'] if a['name'] == name))
            elif close or use_ranged:
                self.enemy_attack(m, p, ranged=use_ranged)
            elif not m.restrained:
                m.movement += 30
                self.move(m, p.pos)
        m.whipped = False
        m.reaction = True

    def tick_wave(self, actor):
        if self.dragon and self.clock >= self.dragon_until:
            self.dragon = False
        if not self.web or not self.web.concentrating:
            return
        for cell, expiry in list(self.web.fires.items()):
            if self.clock >= expiry:
                self.web.burned.add(cell)
                del self.web.fires[cell]
                self.emit('web_burned', cell=cell)
        for m in self.enemies:
            if m.restrained and not self.active_web(m.pos):
                m.restrained = False
        for p in self.pcs:
            if p.name in self.pc_restrained and not self.active_web(p.pos):
                self.pc_restrained.remove(p.name)
        if self.active_web(actor.pos) and self.web.cell(actor.pos) in self.web.fires:
            if isinstance(actor, Enemy):
                self.damage_enemy(actor, self.roll(2, 4), 'fire')
            elif actor.name not in self.web.immune:
                self.hurt(actor, self.roll(2, 4), 'fire')

    def run(self):
        self.dodging = None
        for rnd in range(1, self.wave_config.max_rounds+1):
            self.round = rnd
            for _, name in self.order:
                if not any(m.up for m in self.enemies):
                    return self.result('win')
                if all(p.dead for p in self.pcs):
                    return self.result('defeat')
                self.clock += 1
                actor = self.by_name[name]
                if actor.dead:
                    continue
                self.current_actor, self.phase = name, 'turn'
                for p in self.pcs:
                    if p.song and self.clock >= p.song_until:
                        p.song = False
                if actor is self.F:
                    self.dodging = None
                self.tick_wave(actor)
                if isinstance(actor, Enemy):
                    if actor.up:
                        self.enemy_turn(actor)
                else:
                    self.pc_turn(actor)
                    if self.paralyzed[name] and (self.clock >= self.paralyzed[name] or self.d20()+actor.saves['con'] >= 10):
                        self.paralyzed[name] = 0
                self.emit('turn_end', target=name, hp=getattr(actor, 'hp', None))
            if not any(m.up for m in self.enemies):
                return self.result('win')
        return self.result('timeout')

    def result(self, status):
        return dict(status=status, rounds=self.round, falls=self.falls, dead=sum(p.dead for p in self.pcs),
                    standing=sum(p.up for p in self.pcs), remaining=sum(m.hp for m in self.enemies),
                    hp={p.name: p.hp for p in self.pcs}, first_fall_round=self.first_fall_round,
                    used=dict(self.used), events=self.events if self.record else None)


def wilson(successes, runs):
    z, p = 1.959963984540054, successes / runs
    den = 1 + z*z/runs
    mid = (p+z*z/(2*runs))/den
    half = z*math.sqrt(p*(1-p)/runs+z*z/(4*runs*runs))/den
    return [max(0, mid-half), min(1, mid+half)]


def simulate(config, runs=10000, seed=20261008):
    if runs <= 0:
        raise ValueError('Число боёв положительное')
    rng = random.Random(seed)
    wins = timeouts = falls = falls_sq = deaths = clean = rounds = win_falls = win_deaths = 0
    used = dict.fromkeys(('p3', 'p2', 'p1', 'enhanced', 'oil', 'balls'), 0)
    for _ in range(runs):
        r = WaveBattle(config, rng).run()
        won = r['status'] == 'win'
        wins += won
        timeouts += r['status'] == 'timeout'
        clean += won and not r['dead']
        falls += r['falls']
        falls_sq += r['falls']**2
        deaths += r['dead']
        rounds += r['rounds']
        if won:
            win_falls += r['falls']
            win_deaths += r['dead']
        for k in used:
            used[k] += r['used'][k]
    return dict(runs=runs, wins=wins, defeats=runs-wins-timeouts, timeouts=timeouts,
                win_rate=wins/runs, win_ci95=wilson(wins, runs),
                clean_win_rate=clean/runs, clean_win_ci95=wilson(clean, runs),
                mean_falls=falls/runs,
                falls_se=math.sqrt(max(0, (falls_sq-falls*falls/runs)/(runs-1))/runs) if runs > 1 else None,
                mean_deaths=deaths/runs, mean_rounds=rounds/runs,
                mean_win_falls=win_falls/wins if wins else None,
                mean_win_deaths=win_deaths/wins if wins else None,
                mean_used={k: v/runs for k, v in used.items()})
