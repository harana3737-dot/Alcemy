"""Бой с авторским Вордтом: правила 2014, явные допущения о боссе.

Координаты — центры условных жетонов на сетке 5 фт. Диагональ стоит
5 фт (вариант сетки SRD). Это модель открытой площадки, не VTT:
размеры оснований, стены, укрытия и высота не задаются.
"""
from dataclasses import dataclass, field, asdict
import math
import random

TALIS, LAEL, FAENON, BOSS = 'Талис', 'Лаэль', 'Фаэнон', 'Вордт'


def distance(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


@dataclass(frozen=True)
class Config:
    hp: int = 130
    ac: int = 15
    speed: int = 40
    reach: int = 5
    approach: bool = True
    potions: bool = True
    legend_attacks: int = 0
    leap: bool = False
    legendary_resistances: int = 0
    leap_distance: int = 50
    leap_dc: int = 15
    leap_dice: tuple = (2, 6, 5)
    legend_attack_cost: int = 1
    leap_cost: int = 1
    legend_points: int | None = None
    breath_dice: tuple = (10, 6)
    breath_dc: int = 14
    breath_range: int = 30
    breath_replaces: int = 1
    attack_bonus: int = 7
    attack_dice: tuple = (2, 8, 5)
    attacks: int = 2
    rage: bool = True
    max_rounds: int = 50
    policy: str = 'фронт'
    precreated_slot: bool = True
    song_precast: bool = False
    absorb_elements: bool = False  # есть в книге, подготовка не подтверждена
    boss_policy: str = 'attack_if_in_range'

    def __post_init__(self):
        for key in ('hp', 'ac', 'max_rounds', 'legend_attack_cost', 'leap_cost'):
            if getattr(self, key) <= 0:
                raise ValueError(f'{key} должен быть положительным')
        for key in ('speed', 'reach', 'leap_distance', 'breath_range'):
            if getattr(self, key) < 0 or getattr(self, key) % 5:
                raise ValueError(f'{key}: неотрицательное число, кратное 5 фт')
        for key in ('legend_attacks', 'legendary_resistances', 'breath_replaces', 'attacks'):
            if getattr(self, key) < 0:
                raise ValueError(f'{key} не может быть отрицательным')
        if self.legend_points is not None and self.legend_points < 0:
            raise ValueError('legend_points не может быть отрицательным')
        if self.policy not in ('фронт', 'фокус'):
            raise ValueError('policy: фронт или фокус')
        if self.boss_policy not in ('attack_if_in_range', 'escape'):
            raise ValueError('boss_policy: attack_if_in_range или escape')

    @classmethod
    def from_env(cls, env):
        ints = {'HP': 'hp', 'SPEED': 'speed', 'REACH': 'reach', 'LA': 'legend_attacks',
                'LR': 'legendary_resistances', 'LEAP_DISTANCE': 'leap_distance',
                'BREATH_REPLACES': 'breath_replaces', 'MAX_ROUNDS': 'max_rounds',
                'LEGEND_POINTS': 'legend_points', 'LEAP_COST': 'leap_cost',
                'LEGEND_ATTACK_COST': 'legend_attack_cost'}
        flags = {'APPROACH': 'approach', 'POTIONS': 'potions', 'LEAP': 'leap',
                 'SONG_PRECAST': 'song_precast', 'ABSORB': 'absorb_elements',
                 'PRECREATED_SLOT': 'precreated_slot'}
        values = {key: int(env[name]) for name, key in ints.items() if name in env}
        for name, key in flags.items():
            if name in env:
                if env[name] not in ('0', '1'):
                    raise ValueError(f'{name}: 0 или 1')
                values[key] = env[name] == '1'
        if 'BOSS_POLICY' in env:
            values['boss_policy'] = env['BOSS_POLICY']
        return cls(**values)


@dataclass
class PC:
    name: str
    hp: int
    ac: int
    initiative: int
    saves: dict
    pos: tuple
    speed: int = 30
    slots: dict = field(default_factory=lambda: {1: 4, 2: 3})
    resistance: set = field(default_factory=set)
    max_hp: int = field(init=False)
    temp_hp: int = 0
    reaction: bool = True
    shield_on: bool = False
    shield_budget: int = 2
    prone: bool = False
    dead: bool = False
    stable: bool = False
    death_successes: int = 0
    death_failures: int = 0
    action: bool = True
    bonus: bool = True
    movement: int = 30
    bonus_spell: bool = False
    own_spells: list = field(default_factory=list)
    song: bool = False
    song_until: int = 0
    song_uses: int = 0
    sorcery: int = 0
    metamagic_only: int = 0
    quick_used: bool = False
    loh: int = 0
    potions: list = field(default_factory=list)
    absorb_cold: bool = False
    careful_free: bool = True

    def __post_init__(self):
        self.max_hp = self.hp

    @property
    def up(self):
        return self.hp > 0 and not self.dead

    @property
    def armor(self):
        return self.ac + (4 if self.song else 0) + (5 if self.shield_on else 0)


@dataclass
class Web:
    bounds: tuple
    owner: str = TALIS
    concentrating: bool = True
    heightened_pending: bool = True
    fires: dict = field(default_factory=dict)
    burned: set = field(default_factory=set)
    immune: set = field(default_factory=set)

    def cell(self, pos):
        return (pos[0] // 5, pos[1] // 5)

    def contains(self, pos):
        x0, y0, x1, y1 = self.bounds
        return (self.concentrating and x0 <= pos[0] < x1 and y0 <= pos[1] < y1
                and self.cell(pos) not in self.burned)


class Battle:
    def __init__(self, config=None, tactic='паутина', rng=None, record=False):
        self.config = config or Config()
        self.tactic = tactic
        if tactic not in ('урон', 'паутина'):
            raise ValueError('tactic: урон или паутина')
        self.rng = rng or random.Random(1)
        self.record = record
        self.events = []
        self.round = 0
        self.clock = 0
        self.current_actor = None
        self.phase = 'setup'
        self.falls = 0
        self.web = None
        self.restrained = False
        self.mon_hp = self.config.hp
        self.mon_pos = (50 if self.config.approach else 5, 0)
        self.mon_reaction = True
        self.mon_movement = self.config.speed
        self.mon_movement_spent = 0
        self.breath_ready = True
        self.lr = self.config.legendary_resistances
        self.legend_points = 0
        self.legend_attacks_left = 0
        self.leap_left = 0
        self.pcs = [
            PC(TALIS, 34, 15, 2, dict(dex=2, con=5, wis=1, str=-1, int=0, cha=6), (0, -15), resistance={'cold'}),
            PC(LAEL, 27, 16, 3, dict(dex=3, con=2, wis=2, str=-1, int=6, cha=0), (0, 15)),
            PC(FAENON, 41, 16, 3, dict(dex=3, con=2, wis=3, str=6, int=2, cha=5), (0, 0), slots={1: 4, 2: 0}),
        ]
        self.T, self.L, self.F = self.pcs
        self.T.sorcery, self.T.metamagic_only = 4, 2
        if self.config.precreated_slot:
            self.T.sorcery -= 3
            self.T.slots[2] += 1
        self.L.slots[1] -= 1  # Доспехи мага после последнего отдыха
        self.L.song_uses = 2
        if self.config.song_precast:
            self.L.song = True
            self.L.song_until = 40
            self.L.song_uses -= 1
        self.F.shield_budget = 0
        self.F.loh = 20
        if self.config.potions:
            self.T.temp_hp = self.roll(1, 4) + 4  # имеющийся свиток, не ячейка
            self.T.potions = [3, 3, 2]
        self.refresh_legends()
        self.order = sorted([(self.d20() + p.initiative, p.name) for p in self.pcs]
                            + [(self.d20(), BOSS)], key=lambda v: -v[0])
        self.emit('setup', parameters=asdict(self.config), positions={p.name: p.pos for p in self.pcs},
                  boss_position=self.mon_pos, slots={p.name: dict(p.slots) for p in self.pcs})

    def emit(self, event, **data):
        if self.record:
            self.events.append(dict(round=self.round, clock=self.clock, actor=self.current_actor,
                                    phase=self.phase, event=event, **data))

    def roll(self, n, sides):
        return sum(self.rng.randint(1, sides) for _ in range(n))

    def d20(self, advantage=False, disadvantage=False):
        a = self.rng.randint(1, 20)
        if bool(advantage) == bool(disadvantage):
            return a
        b = self.rng.randint(1, 20)
        return max(a, b) if advantage else min(a, b)

    def active_web(self, pos):
        return self.web is not None and self.web.contains(pos)

    def stop_web(self, reason):
        if self.web and self.web.concentrating:
            self.web.concentrating = False
            self.restrained = False
            self.emit('concentration_ended', reason=reason)

    def spend_meta(self, cost):
        if self.T.metamagic_only + self.T.sorcery < cost:
            return False
        special = min(cost, self.T.metamagic_only)
        self.T.metamagic_only -= special
        self.T.sorcery -= cost - special
        self.emit('metamagic', cost=cost, ordinary=self.T.sorcery, feat=self.T.metamagic_only)
        return True

    def begin_pc_turn(self, p):
        if p.song and self.clock >= p.song_until:
            p.song = False
            self.emit('bladesong_ended', reason='duration', target=p.name)
        p.reaction = True
        p.shield_on = False
        p.absorb_cold = False
        p.action, p.bonus = True, True
        p.movement = p.speed + (10 if p.song else 0)
        p.bonus_spell = False
        p.own_spells = []
        self.emit('turn_start', target=p.name, hp=p.hp, armor=p.armor, reaction=p.reaction, pos=p.pos)
        if p.dead:
            return
        if p.hp == 0 and not p.stable:
            face = self.d20()
            if face == 20:
                self.heal(p, 1, 'death_save_20')
            elif face >= 10:
                p.death_successes += 1
                if p.death_successes >= 3:
                    p.stable = True
                    p.death_successes = p.death_failures = 0
            else:
                p.death_failures += 2 if face == 1 else 1
                if p.death_failures >= 3:
                    p.dead = True
            self.emit('death_save', target=p.name, face=face, stable=p.stable, dead=p.dead)
        if p.up and p.prone and p.movement >= p.speed // 2:
            # Вставание стоит половину полной скорости, включая Песнь.
            p.movement -= (p.speed + (10 if p.song else 0)) // 2
            p.prone = False
            self.emit('stand', target=p.name, movement_left=p.movement)

    def heal(self, p, amount, source):
        if p.dead:
            return False
        before = p.hp
        p.hp = min(p.max_hp, p.hp + amount)
        if p.hp > 0:
            p.stable = False
            p.death_failures = p.death_successes = 0
        self.emit('heal', target=p.name, amount=p.hp - before, source=source, hp=p.hp)
        return True

    def can_react_spell(self, p):
        return p.up and p.reaction and not (self.current_actor == p.name and p.bonus_spell)

    def cast(self, p, spell, level, kind='action'):
        if not p.up or (level and p.slots.get(level, 0) <= 0):
            return False
        if kind == 'reaction':
            if not self.can_react_spell(p):
                return False
        elif kind == 'bonus':
            if not p.bonus or any(k != 'action' or lv != 0 for k, lv in p.own_spells):
                return False
        else:
            if not p.action or p.bonus_spell and level:
                return False
        if level:
            p.slots[level] -= 1
        if kind == 'reaction':
            p.reaction = False
        elif kind == 'bonus':
            p.bonus = False
            p.bonus_spell = True
        else:
            p.action = False
        if self.current_actor == p.name:
            p.own_spells.append((kind, level))
        self.emit('spell', target=p.name, spell=spell, level=level, kind=kind, slots=dict(p.slots))
        return True

    def lowest_slot(self, p):
        return next((lv for lv in (1, 2) if p.slots.get(lv, 0)), None)

    def shield(self, p, total, critical=False):
        if critical or total < p.armor or total >= p.armor + 5 or p.shield_budget <= 0:
            return False
        lv = self.lowest_slot(p)
        if lv and self.cast(p, 'Щит', lv, 'reaction'):
            p.shield_on = True
            p.shield_budget -= 1
            self.emit('shield', target=p.name, armor=p.armor)
            return True
        return False

    def hurt(self, p, amount, damage_type, critical=False):
        if p.dead or amount <= 0:
            return
        received = amount // 2 if damage_type in p.resistance or damage_type == 'cold' and p.absorb_cold else amount
        if received <= 0:
            return
        absorbed = min(p.temp_hp, received)
        p.temp_hp -= absorbed
        hp_damage = received - absorbed
        before = p.hp
        if before > 0:
            p.hp = max(0, before - hp_damage)
            if p.hp == 0:
                self.falls += 1
                p.prone = True
                p.stable = False
                p.death_failures = p.death_successes = 0
            if hp_damage - before >= p.max_hp:
                p.dead = True
        elif received:
            p.stable = False
            p.death_failures += 2 if critical else 1
            if hp_damage >= p.max_hp or p.death_failures >= 3:
                p.dead = True
        self.emit('damage', target=p.name, damage_type=damage_type, received=received,
                  temporary=absorbed, hp_damage=hp_damage, hp=p.hp, dead=p.dead)
        if p.song and not p.up:
            p.song = False
            self.emit('bladesong_ended', reason='incapacitated', target=p.name)
        if p is self.T and self.web and self.web.concentrating:
            if not p.up:
                self.stop_web('incapacitated')
            else:
                dc = max(10, received // 2)
                face = self.d20()
                self.emit('concentration_save', target=p.name, face=face, dc=dc, total=face + p.saves['con'])
                if face + p.saves['con'] < dc:
                    self.stop_web('damage')

    def hurt_boss(self, amount, damage_type='force'):
        if damage_type == 'cold':
            amount //= 2
        self.mon_hp = max(0, self.mon_hp - amount)
        self.emit('boss_damage', damage_type=damage_type, amount=amount, hp=self.mon_hp)
        if damage_type == 'fire' and self.active_web(self.mon_pos):
            cell = self.web.cell(self.mon_pos)
            self.web.fires.setdefault(cell, self.clock + len(self.order))
            self.emit('web_fire', cell=cell, expires=self.web.fires[cell])

    def cast_web(self):
        if distance(self.T.pos, self.mon_pos) > 60:
            return False
        x, y = self.mon_pos
        dx, dy = x - self.T.pos[0], y - self.T.pos[1]
        if abs(dx) >= abs(dy):
            bounds = (x, y - 10, x + 20, y + 10) if dx >= 0 else (x - 15, y - 10, x + 5, y + 10)
        else:
            bounds = (x - 10, y, x + 10, y + 20) if dy >= 0 else (x - 10, y - 15, x + 10, y + 5)
        # Сначала выбираем край куба, который не захватывает союзников.
        placements = [bounds, (x, y - 10, x + 20, y + 10), (x - 15, y - 10, x + 5, y + 10),
                      (x - 10, y, x + 10, y + 20), (x - 10, y - 15, x + 10, y + 5)]
        inside = lambda b: [p for p in self.pcs if not p.dead and Web(b).contains(p.pos)]
        bounds = min(placements, key=lambda b: len(inside(b)))
        friends = inside(bounds)
        immune = set()
        if friends and not (self.T.careful_free or self.T.sorcery + self.T.metamagic_only >= 1):
            return False
        if not self.cast(self.T, 'Паутина', 2):
            return False
        self.stop_web('new_concentration')
        if friends and (self.T.careful_free or self.T.sorcery + self.T.metamagic_only >= 1):
            if self.T.careful_free:
                self.T.careful_free = False
            else:
                self.spend_meta(1)
            immune = {p.name for p in friends}
            heightened = False  # две метамагии на одном заклинании не складываем
        else:
            heightened = self.spend_meta(3)
        self.web = Web(bounds, heightened_pending=heightened, immune=immune)
        self.emit('web_created', bounds=bounds, heightened=heightened, immune=sorted(immune))
        return True

    def web_save(self, source):
        if not self.active_web(self.mon_pos):
            return
        heightened = self.web.heightened_pending
        self.web.heightened_pending = False
        face = self.d20(disadvantage=self.restrained or heightened)
        failed = face < 14
        if failed and self.lr:
            self.lr -= 1
            failed = False
            self.emit('legendary_resistance', charges=self.lr)
        if failed:
            self.restrained = True
            self.mon_movement = 0
        self.emit('web_save', source=source, face=face, restrained=self.restrained)

    def escape_web(self):
        face = self.d20()
        success = face + 5 >= 14
        if success:
            self.restrained = False
            self.mon_movement = max(0, self.config.speed - self.mon_movement_spent)
        self.emit('web_escape', face=face, total=face + 5, success=success)
        return success

    def tick_web(self):
        if not self.web or not self.web.concentrating:
            return
        for cell, expiry in list(self.web.fires.items()):
            if self.clock >= expiry:
                self.web.burned.add(cell)
                del self.web.fires[cell]
                self.emit('web_burned', cell=cell)
        if self.restrained and not self.active_web(self.mon_pos):
            self.restrained = False
        for p in self.pcs:
            if (self.current_actor == p.name and p.name not in self.web.immune
                    and self.active_web(p.pos) and self.web.cell(p.pos) in self.web.fires):
                self.hurt(p, self.roll(2, 4), 'fire')
        if self.current_actor == BOSS and self.phase == 'turn' and self.active_web(self.mon_pos) and self.web.cell(self.mon_pos) in self.web.fires:
            self.hurt_boss(self.roll(2, 4), 'fire')

    def choose(self, candidates):
        if self.config.policy == 'фокус':
            return min(candidates, key=lambda p: (not p.up, p.hp, distance(p.pos, self.mon_pos)))
        return self.rng.choices(candidates, weights=[3 if p is self.F else 1.5 for p in candidates])[0]

    def monster_attack(self, p, opportunity=False):
        if self.mon_hp <= 0 or p.dead or distance(self.mon_pos, p.pos) > self.config.reach:
            return False
        face = self.d20(advantage=p.prone or not p.up, disadvantage=self.restrained)
        total = face + self.config.attack_bonus
        critical = face == 20
        hit = face != 1 and (critical or total >= p.armor)
        if hit and not self.shield(p, total, critical):
            critical = critical or not p.up and distance(self.mon_pos, p.pos) <= 5
            n, sides, add = self.config.attack_dice
            self.hurt(p, self.roll(n * (2 if critical else 1), sides) + add, 'bludgeoning', critical)
        else:
            hit = False
        self.emit('boss_attack', target=p.name, face=face, total=total, hit=hit,
                  critical=critical, opportunity=opportunity, distance=distance(self.mon_pos, p.pos))
        return True

    def weapon_attack(self, p, opportunity=False):
        if not p.up or self.mon_hp <= 0 or distance(p.pos, self.mon_pos) > 5:
            return False
        face = self.d20(advantage=self.restrained, disadvantage=p.prone)
        hit = face != 1 and (face == 20 or face + 6 >= self.config.ac)
        if hit:
            critical = 2 if face == 20 else 1
            amount = self.roll(2 * critical, 6) + 4
            radiant = 0
            # Последняя ячейка I сохраняется под Лечение ран.
            if p.slots.get(1, 0) > 1:
                p.slots[1] -= 1
                radiant = self.roll(2 * critical, 8)
                self.emit('smite', target=p.name, level=1, slots=dict(p.slots))
            self.hurt_boss(amount, 'slashing')  # магический двуручный меч
            if radiant:
                self.hurt_boss(radiant, 'radiant')
        self.emit('weapon_attack', target=p.name, face=face, hit=hit, opportunity=opportunity,
                  distance=distance(p.pos, self.mon_pos))
        return True

    def path(self, start, goal, budget, boss=False, stop=0):
        pos, used, route = start, 0, []
        occupied = {p.pos for p in self.pcs if not p.dead and p.pos != start}
        if not boss:
            occupied.add(self.mon_pos)
        mover = next((p for p in self.pcs if p.pos == start), None) if not boss else None
        immune = bool(mover and self.web and mover.name in self.web.immune)
        for _ in range(30):
            if distance(pos, goal) <= stop:
                break
            candidates = [(pos[0] + x, pos[1] + y) for x in (-5, 0, 5) for y in (-5, 0, 5) if x or y]
            candidates = [q for q in candidates if q not in occupied and distance(q, goal) < distance(pos, goal)]
            if not boss and not immune:
                candidates = [q for q in candidates if not self.active_web(q)]  # Фаэнон не входит в зону
            if not candidates:
                break
            nxt = min(candidates, key=lambda q: (distance(q, goal), abs(q[0] - goal[0]) + abs(q[1] - goal[1])))
            cost = 10 if self.active_web(nxt) and not immune else 5
            if used + cost > budget:
                break
            used += cost
            route.append((nxt, used))
            pos = nxt
        return route

    def move_pc(self, p, goal, stop=0):
        for pos, _ in self.path(p.pos, goal, p.movement, stop=stop):
            if not p.up or self.mon_hp <= 0:
                break
            if self.mon_reaction and distance(p.pos, self.mon_pos) <= self.config.reach < distance(pos, self.mon_pos):
                self.mon_reaction = False
                self.monster_attack(p, opportunity=True)
                if not p.up:
                    break
            cost = 10 if self.active_web(pos) and not (self.web and p.name in self.web.immune) else 5
            p.movement -= cost
            old, p.pos = p.pos, pos
            self.emit('move', target=p.name, start=old, end=pos, movement_left=p.movement)

    def move_monster(self, goal, budget=None, own_turn=True, stop=5):
        if self.restrained:
            return
        allowance = self.mon_movement if budget is None else budget
        spent = 0
        for pos, total in self.path(self.mon_pos, goal, allowance, boss=True, stop=stop):
            if self.mon_hp <= 0 or self.restrained:
                break
            if self.F.up and self.F.reaction and distance(self.mon_pos, self.F.pos) <= 5 < distance(pos, self.F.pos):
                self.F.reaction = False
                self.weapon_attack(self.F, opportunity=True)
                if self.mon_hp <= 0:
                    break
            was_inside = self.active_web(self.mon_pos)
            old, self.mon_pos = self.mon_pos, pos
            spent = total
            self.emit('boss_move', start=old, end=pos, own_turn=own_turn)
            if not self.active_web(pos):
                self.restrained = False
            elif not was_inside and own_turn:
                self.web_save('entry_during_own_turn')
        if budget is None:
            self.mon_movement_spent += spent
            self.mon_movement = max(0, allowance - spent) if not self.restrained else 0

    def cone_targets(self, origin=None):
        origin = origin or self.mon_pos
        living = [p for p in self.pcs if not p.dead]
        angles = [math.atan2(p.pos[1] - origin[1], p.pos[0] - origin[0]) for p in living if p.pos != origin]
        aims = list(angles)
        for i, a in enumerate(angles):
            for b in angles[i + 1:]:
                delta = (b - a + math.pi) % (2 * math.pi) - math.pi
                aims.append(a + delta / 2)
        best, score = [], (-1, -1)
        for angle in aims:
            ux, uy = math.cos(angle), math.sin(angle)
            targets = []
            for p in living:
                x, y = p.pos[0] - origin[0], p.pos[1] - origin[1]
                forward, sideways = x * ux + y * uy, abs(x * uy - y * ux)
                if 0 < forward <= self.config.breath_range + 1e-8 and sideways <= forward / 2 + 1e-8:
                    targets.append(p)
            value = (sum(p.up for p in targets), sum(0.5 if 'cold' in p.resistance else 1 for p in targets))
            if value > score:
                score, best = value, targets
        return best

    def breathe(self, targets=None):
        targets = self.cone_targets() if targets is None else targets
        if not self.breath_ready or not targets or self.mon_hp <= 0:
            return False
        self.breath_ready = False
        amount = self.roll(*self.config.breath_dice)
        self.emit('breath', targets=[p.name for p in targets], raw_damage=amount, position=self.mon_pos)
        for p in targets:
            face = self.d20()
            saved = face + p.saves['con'] >= self.config.breath_dc
            damage = amount // 2 if saved else amount
            if p is self.L and self.config.absorb_elements and 'cold' not in p.resistance:
                lv = self.lowest_slot(p)
                if lv and self.cast(p, 'Поглощение стихий', lv, 'reaction'):
                    p.absorb_cold = True
            self.emit('breath_save', target=p.name, face=face, saved=saved)
            self.hurt(p, damage, 'cold')
        return True

    def refresh_legends(self):
        c = self.config
        self.legend_attacks_left = c.legend_attacks
        self.leap_left = int(c.leap)
        self.legend_points = c.legend_points if c.legend_points is not None else c.legend_attacks * c.legend_attack_cost + int(c.leap) * c.leap_cost

    def legend(self):
        if self.mon_hp <= 0 or self.legend_points <= 0:
            return
        living = [p for p in self.pcs if not p.dead]
        awake = [p for p in living if p.up]
        candidates = awake or living
        if not candidates:
            return
        if self.leap_left and not self.restrained and self.legend_points >= self.config.leap_cost:
            reachable = [p for p in candidates if distance(p.pos, self.mon_pos) <= self.config.leap_distance + 5]
            if reachable:
                target = self.choose(reachable)
                self.leap_left -= 1
                self.legend_points -= self.config.leap_cost
                self.emit('legendary_action', action='leap', points_left=self.legend_points)
                self.move_monster(target.pos, self.config.leap_distance, own_turn=False)
                if self.mon_hp > 0 and distance(target.pos, self.mon_pos) <= 5:
                    face = self.d20()
                    failed = not target.up or face + target.saves['dex'] < self.config.leap_dc
                    if failed:
                        target.prone = True
                        self.hurt(target, self.roll(*self.config.leap_dice[:2]) + self.config.leap_dice[2], 'bludgeoning')
                    self.emit('leap_save', target=target.name, face=face, failed=failed, prone=target.prone)
                return  # только одно легендарное действие в этом окне
        eligible = [p for p in candidates if distance(p.pos, self.mon_pos) <= self.config.reach]
        if self.legend_attacks_left and eligible and self.legend_points >= self.config.legend_attack_cost:
            self.legend_attacks_left -= 1
            self.legend_points -= self.config.legend_attack_cost
            self.emit('legendary_action', action='attack', points_left=self.legend_points)
            self.monster_attack(self.choose(eligible))

    def boss_turn(self):
        self.mon_reaction = True
        self.mon_movement = self.config.speed
        self.mon_movement_spent = 0
        self.refresh_legends()
        if not self.breath_ready and self.rng.randint(1, 6) >= 5:
            self.breath_ready = True
            self.emit('breath_recharge')
        if self.active_web(self.mon_pos):
            self.web_save('start_of_turn')
        if self.mon_hp <= 0:
            return
        candidates = [p for p in self.pcs if p.up] or [p for p in self.pcs if not p.dead]
        if not candidates:
            return
        target = self.choose(candidates)
        if self.restrained:
            if self.breath_ready and self.cone_targets() and self.config.boss_policy != 'escape':
                pass  # дыхание разрешено и у опутанного
            elif self.config.boss_policy == 'escape' or not any(distance(p.pos, self.mon_pos) <= self.config.reach for p in candidates):
                self.escape_web()
                if not self.restrained:
                    self.move_monster(target.pos, stop=self.config.reach)
                return
        if not self.restrained:
            path = [(self.mon_pos, 0)] + self.path(self.mon_pos, target.pos, self.mon_movement, boss=True, stop=self.config.reach)
            if self.breath_ready:
                best = max(path, key=lambda item: (sum(p.up for p in self.cone_targets(item[0])), -item[1]))
                if self.cone_targets(best[0]):
                    self.move_monster(best[0], stop=0)
                else:
                    self.move_monster(target.pos, stop=self.config.reach)
            else:
                self.move_monster(target.pos, stop=self.config.reach)
        if self.restrained and not (self.breath_ready and self.cone_targets()) and not any(distance(p.pos, self.mon_pos) <= self.config.reach for p in candidates):
            self.escape_web()
            if not self.restrained:
                self.move_monster(target.pos, stop=self.config.reach)
            return
        used_breath = self.breathe() if self.breath_ready else False
        count = self.config.attacks + int(self.config.rage and self.mon_hp <= self.config.hp // 2)
        if used_breath:
            count = max(0, count - self.config.breath_replaces)
        if not self.restrained:
            self.move_monster(target.pos, stop=self.config.reach)
        if not used_breath and not self.restrained and not any(
                distance(p.pos, self.mon_pos) <= self.config.reach for p in candidates):
            # Если действие не потрачено на дыхание/освобождение, можно рывком сблизиться.
            self.mon_movement += self.config.speed
            self.emit('boss_action', action='dash')
            self.move_monster(target.pos, stop=self.config.reach)
            return
        for _ in range(count):
            if self.mon_hp <= 0:
                break
            eligible = [p for p in self.pcs if p.up and distance(p.pos, self.mon_pos) <= self.config.reach]
            if not eligible:
                eligible = [p for p in self.pcs if not p.dead and distance(p.pos, self.mon_pos) <= self.config.reach]
            if not eligible:
                break
            self.monster_attack(target if target in eligible else self.choose(eligible))

    def offensive_slot(self, p):
        if p.slots.get(2, 0):
            return 2
        if p.slots.get(1, 0) > min(p.shield_budget, p.slots.get(1, 0)):
            return 1
        return 0

    def cantrip(self, p):
        if distance(p.pos, self.mon_pos) > 120:
            return False
        spell, sides, damage_type = ('Леденящее прикосновение', 8, 'necrotic')
        if p is self.L and not self.active_web(self.mon_pos):
            spell, sides, damage_type = ('Огненный снаряд', 10, 'fire')
        if self.cast(p, spell, 0):
            face = self.d20(advantage=self.restrained,
                            disadvantage=p.prone or distance(p.pos, self.mon_pos) <= 5)
            if face != 1 and (face == 20 or face + 6 >= self.config.ac):
                self.hurt_boss(self.roll(2 if face == 20 else 1, sides), damage_type)
            self.emit('spell_attack', target=p.name, spell=spell, face=face, distance=distance(p.pos, self.mon_pos))

    def orb(self, level, kind='action'):
        if distance(self.T.pos, self.mon_pos) > 90 or not self.cast(self.T, 'Хроматический шар', level, kind):
            return False
        face = self.d20(advantage=self.restrained,
                        disadvantage=self.T.prone or distance(self.T.pos, self.mon_pos) <= 5)
        if face != 1 and (face == 20 or face + 6 >= self.config.ac):
            self.hurt_boss(self.roll((level + 2) * (2 if face == 20 else 1), 8), 'acid')
        self.emit('spell_attack', target=TALIS, spell='Хроматический шар', face=face, distance=distance(self.T.pos, self.mon_pos))
        return True

    def kite(self, p):
        if distance(p.pos, self.mon_pos) >= 35:
            return
        dx = 1 if p.pos[0] >= self.mon_pos[0] else -1
        dy = 1 if p.pos[1] >= self.mon_pos[1] else -1
        goal = (p.pos[0] + dx * 35, p.pos[1] + dy * 35)
        self.move_pc(p, goal)

    def pc_turn(self, p):
        self.begin_pc_turn(p)
        if not p.up:
            return
        if p is self.F:
            down = [q for q in self.pcs if not q.dead and not q.up]
            if down and (p.loh or p.slots[1]):
                target = min(down, key=lambda q: distance(q.pos, p.pos))
                self.move_pc(p, target.pos, stop=5)
                if distance(p.pos, target.pos) <= 5 and p.up:
                    if p.loh:
                        amount = min(10, p.loh)
                        p.loh -= amount
                        p.action = False
                        self.heal(target, amount, 'Возложение рук')
                        self.emit('action', action='lay_on_hands', target=target.name)
                    elif self.cast(p, 'Лечение ран', 1):
                        self.heal(target, self.roll(1, 8) + 3, 'Лечение ран')
                    return
            self.move_pc(p, self.mon_pos, stop=5)
            if p.up and distance(p.pos, self.mon_pos) <= 5:
                p.action = False
                self.weapon_attack(p)
            elif p.up and p.action:
                p.action = False
                p.movement += p.speed
                self.emit('action', action='dash', target=p.name)
                self.move_pc(p, self.mon_pos, stop=5)
            return
        if p is self.L and not p.song and p.song_uses and p.bonus:
            p.bonus = False
            p.song = True
            p.song_until = self.clock + 10 * len(self.order)
            p.song_uses -= 1
            p.movement += 10
            self.emit('bonus_action', action='bladesong', target=p.name, armor=p.armor)
        self.kite(p)
        if not p.up or self.mon_hp <= 0:
            return
        if p is self.L:
            lv = self.offensive_slot(p)
            if distance(p.pos, self.mon_pos) > 120:
                self.move_pc(p, self.mon_pos, stop=120)
            if distance(p.pos, self.mon_pos) <= 120:
                if lv and self.cast(p, 'Волшебные стрелы', lv):
                    self.hurt_boss(self.roll(lv + 2, 4) + lv + 2)
                elif not lv:
                    self.cantrip(p)
            return
        if p.potions and p.hp <= 14 and p.bonus:
            p.bonus = False
            level = p.potions.pop(0)
            amount = self.roll(4, 4) - 1 if level == 3 else self.roll(2, 4) + 1
            self.emit('bonus_action', action='potion', level=level, target=p.name)
            self.heal(p, amount, 'зелье')
        if self.tactic == 'паутина' and self.web is None and p.slots.get(2, 0) and distance(p.pos, self.mon_pos) <= 60:
            self.cast_web()
            return
        lv = self.offensive_slot(p)
        if distance(p.pos, self.mon_pos) > 90:
            self.move_pc(p, self.mon_pos, stop=90)
        if distance(p.pos, self.mon_pos) > 120:
            return
        quick = (self.tactic == 'урон' and not p.quick_used and p.bonus and lv
                 and distance(p.pos, self.mon_pos) <= 90 and not p.own_spells
                 and p.sorcery + p.metamagic_only >= 2)
        if quick:
            self.cantrip(p)  # действием — заговор; бонусным — единственное уровневое
            if self.mon_hp > 0 and self.spend_meta(2):
                p.quick_used = True
                self.orb(lv, 'bonus')
        elif lv and distance(p.pos, self.mon_pos) <= 90:
            self.orb(lv)
        else:
            self.cantrip(p)

    def run(self):
        for rnd in range(1, self.config.max_rounds + 1):
            self.round = rnd
            for _, name in self.order:
                if self.mon_hp <= 0:
                    return self.result('win')
                if all(p.dead for p in self.pcs):
                    return self.result('defeat')
                self.clock += 1
                self.current_actor, self.phase = name, 'turn'
                for p in self.pcs:
                    if p.song and self.clock >= p.song_until:
                        p.song = False
                        self.emit('bladesong_ended', reason='duration', target=p.name)
                self.tick_web()
                if self.mon_hp <= 0:
                    return self.result('win')
                if name == BOSS:
                    self.boss_turn()
                else:
                    p = next(p for p in self.pcs if p.name == name)
                    had_turn = not p.dead
                    if had_turn:
                        self.pc_turn(p)
                    self.current_actor, self.phase = BOSS, 'legendary'
                    # Только после состоявшегося хода другого существа.
                    if had_turn:
                        self.legend()
                self.emit('turn_end', hp=self.mon_hp, falls=self.falls)
            if self.mon_hp <= 0:
                return self.result('win')
        return self.result('timeout')

    def result(self, status):
        return dict(status=status, rounds=self.round, falls=self.falls,
                    dead=sum(p.dead for p in self.pcs), standing=sum(p.up for p in self.pcs),
                    boss_hp=self.mon_hp, events=self.events if self.record else None)


def simulate_many(config, tactic, runs, seed=1):
    if runs <= 0:
        raise ValueError('runs должен быть положительным')
    rng = random.Random(seed)
    wins = rounds = falls = deaths = timeouts = 0
    for _ in range(runs):
        result = Battle(config, tactic, rng).run()
        if result['status'] == 'win':
            wins += 1
            rounds += result['rounds']
            falls += result['falls']
            deaths += result['dead']
        elif result['status'] == 'timeout':
            timeouts += 1
    rate = wins / runs
    z = 1.959963984540054
    den = 1 + z * z / runs
    center = (rate + z * z / (2 * runs)) / den
    half = z * math.sqrt(rate * (1 - rate) / runs + z * z / (4 * runs * runs)) / den
    return dict(runs=runs, wins=wins, defeats=runs - wins - timeouts, timeouts=timeouts,
                win_rate=rate, win_ci95=[center - half, center + half],
                mean_win_rounds=rounds / wins if wins else None,
                mean_win_falls=falls / wins if wins else None,
                mean_win_deaths=deaths / wins if wins else None)
