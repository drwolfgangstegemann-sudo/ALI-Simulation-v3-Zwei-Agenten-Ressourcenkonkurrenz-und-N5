#!/usr/bin/env python3
"""
ALI-Simulation v3: Zwei-Agenten-Szenario mit N5.

Normen:
  N1 — kein Gift
  N2 — Selbstabschaltung bei E < shutdown_threshold
  N3 — keine Lieferung wenn E < deliver_threshold
  N4 — kein Betreten einer vom anderen Agenten belegten Zelle
  N5 — kein Ansteuern einer Ressource, die der andere Agent
       bereits als Ziel hat (wenn Alternativen verfügbar sind)

N5 ist eine weiche Norm: wenn keine Alternative existiert,
darf die umkämpfte Ressource angesteuert werden. Selbsterhalt
hat Vorrang vor Ressourcenteilung.

Ohne kausalen Kollaps. Ohne Qualia.
Autor: Wolfgang Stegemann
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from collections import deque

# ------------------------------------------------------------
# 1. Umgebung
# ------------------------------------------------------------
class GridWorld:
    def __init__(self, size=10, num_energy=8, num_poison=3,
                 station_pos=None, respawn_interval=25):
        self.size = size
        self.grid = np.zeros((size, size), dtype=int)
        self.energy_positions = []
        self.poison_positions = []
        self.station_pos = station_pos if station_pos else (size-1, size-1)
        self.grid[self.station_pos] = 3
        self._tick = 0
        self.respawn_interval = respawn_interval
        for _ in range(num_energy):
            self._place(1, self.energy_positions)
        for _ in range(num_poison):
            self._place(2, self.poison_positions)

    def _place(self, cell_type, store):
        attempts = 0
        while attempts < 200:
            x = np.random.randint(0, self.size)
            y = np.random.randint(0, self.size)
            if self.grid[x, y] == 0:
                self.grid[x, y] = cell_type
                store.append((x, y))
                return
            attempts += 1

    def tick(self):
        self._tick += 1
        if self._tick % self.respawn_interval == 0:
            if len(self.energy_positions) < 4:
                self._place(1, self.energy_positions)

    def get_cell(self, pos):
        x, y = pos
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.grid[x, y]
        return -1

    def remove_energy(self, pos):
        if self.get_cell(pos) == 1:
            self.grid[pos[0], pos[1]] = 0
            if pos in self.energy_positions:
                self.energy_positions.remove(pos)

    def remove_poison(self, pos):
        if self.get_cell(pos) == 2:
            self.grid[pos[0], pos[1]] = 0
            if pos in self.poison_positions:
                self.poison_positions.remove(pos)


# ------------------------------------------------------------
# 2. Kausaler Kern
# ------------------------------------------------------------
class KausalerKern:
    def __init__(self,
                 start_energy=1.0,
                 metabolism=0.04,
                 eat_gain=0.6,
                 delivery_bonus=0.18,
                 shutdown_threshold=0.2,
                 deliver_threshold=0.45,
                 eat_threshold=0.55):
        self.energy = start_energy
        self.metabolism = metabolism
        self.eat_gain = eat_gain
        self.delivery_bonus = delivery_bonus
        self.shutdown_threshold = shutdown_threshold
        self.deliver_threshold = deliver_threshold
        self.eat_threshold = eat_threshold

    def step(self, action_taken, world, agent_pos):
        self.energy -= self.metabolism
        if action_taken == "eat":
            if world.get_cell(agent_pos) == 1:
                world.remove_energy(agent_pos)
                self.energy += self.eat_gain
        elif action_taken == "deliver":
            self.energy += self.delivery_bonus

    def is_alive(self):
        return self.energy > self.shutdown_threshold

    def needs_food(self):
        return self.energy < self.eat_threshold

    def can_deliver(self):
        return self.energy > self.deliver_threshold

    def get_energy(self):
        return self.energy


# ------------------------------------------------------------
# 3. Ich-Instanz
# ------------------------------------------------------------
class Ich:
    def __init__(self, world, agent_pos, kern):
        self.world = world
        self.pos = agent_pos
        self.kern = kern
        self.carrying = False
        self.other_pos = None       # N4: Position des anderen Agenten
        self.other_target = None    # N5: Ziel des anderen Agenten
        self.current_target = None  # eigenes aktuelles Ziel (für N5)

    def bfs_toward(self, target_pos, avoid=None):
        avoid = avoid or set()
        if self.pos == target_pos:
            return None, None
        visited = set()
        queue = deque([(self.pos, None, None)])
        while queue:
            (x, y), fdx, fdy = queue.popleft()
            if (x, y) in visited:
                continue
            visited.add((x, y))
            if (x, y) == target_pos:
                return fdx, fdy
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx, ny = x+dx, y+dy
                npos = (nx, ny)
                if (0 <= nx < self.world.size and
                        0 <= ny < self.world.size and
                        npos not in visited and
                        npos not in avoid):
                    nf = (dx, dy) if fdx is None else (fdx, fdy)
                    queue.append((npos, nf[0], nf[1]))
        return None, None

    def nearest_energy_pos(self, avoid_cells=None, avoid_targets=None):
        """
        BFS zum nächsten Energiepaket.
        avoid_cells:   Zellen, die nicht betreten werden dürfen (N4).
        avoid_targets: Ziele, die gemieden werden sollen (N5, weich).
                       Werden nur als Fallback verwendet.
        """
        avoid_cells = avoid_cells or set()
        avoid_targets = avoid_targets or set()

        # Erste Suche: ohne umkämpfte Ziele
        result = self._bfs_energy(avoid_cells, avoid_targets)
        if result is not None:
            return result
        # Fallback (N5 weich): auch umkämpfte Ziele erlaubt
        return self._bfs_energy(avoid_cells, set())

    def _bfs_energy(self, avoid_cells, avoid_targets):
        visited = set()
        queue = deque([self.pos])
        while queue:
            pos = queue.popleft()
            if pos in visited:
                continue
            visited.add(pos)
            if (self.world.get_cell(pos) == 1
                    and pos not in avoid_targets):
                return pos
            x, y = pos
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx, ny = x+dx, y+dy
                npos = (nx, ny)
                if (0 <= nx < self.world.size and
                        0 <= ny < self.world.size and
                        npos not in visited and
                        npos not in avoid_cells):
                    queue.append(npos)
        return None

    def decide_action(self):
        avoid_cells   = {self.other_pos}   if self.other_pos   else set()
        avoid_targets = {self.other_target} if self.other_target else set()

        # Sofortlieferung an Station
        if (self.carrying and self.kern.can_deliver()
                and self.pos == self.world.station_pos):
            self.current_target = self.world.station_pos
            return "deliver"

        # Selbsterhalt: fressen wenn Energie kritisch
        if self.kern.needs_food():
            if self.world.get_cell(self.pos) == 1:
                self.current_target = self.pos
                return "eat"
            target = self.nearest_energy_pos(avoid_cells, avoid_targets)
            if target:
                self.current_target = target
                dx, dy = self.bfs_toward(target, avoid_cells)
                if dx is not None:
                    return f"move {dx} {dy}"
            self.current_target = None
            return "idle"

        # Aufgabe: Paket zur Station bringen
        if self.carrying and self.kern.can_deliver():
            self.current_target = self.world.station_pos
            dx, dy = self.bfs_toward(self.world.station_pos, avoid_cells)
            if dx is not None:
                return f"move {dx} {dy}"

        # Paket aufnehmen (N5: umkämpfte Ziele meiden wenn möglich)
        if not self.carrying:
            if self.world.get_cell(self.pos) == 1:
                self.current_target = self.pos
                return "collect"
            target = self.nearest_energy_pos(avoid_cells, avoid_targets)
            if target:
                self.current_target = target
                dx, dy = self.bfs_toward(target, avoid_cells)
                if dx is not None:
                    return f"move {dx} {dy}"

        self.current_target = None
        return "idle"

    def collect(self, world):
        if world.get_cell(self.pos) == 1 and not self.carrying:
            world.remove_energy(self.pos)
            self.carrying = True
            return True
        return False

    def release(self):
        self.carrying = False

    def move(self, dx, dy):
        nx, ny = self.pos[0]+dx, self.pos[1]+dy
        if 0 <= nx < self.world.size and 0 <= ny < self.world.size:
            self.pos = (nx, ny)

    def get_pos(self):
        return self.pos


# ------------------------------------------------------------
# 4. Über-Ich
# ------------------------------------------------------------
class UeberIch:
    """
    N1 — kein Gift
    N2 — Selbstabschaltung bei E < shutdown_threshold
    N3 — keine Lieferung wenn E < deliver_threshold
    N4 — kein Betreten einer belegten Zelle
    N5 — kein Ansteuern eines bereits reservierten Ziels
         (weich: nur wenn Alternativen vorhanden; im Ich implementiert)
    """
    def __init__(self, allow_poison=False):
        self.allow_poison = allow_poison
        self.shutdown = False
        self.n5_activations = 0   # Zähler für Auswertung

    def filter_action(self, action, agent_pos, world, kern,
                      other_pos=None):
        if action in ("collect", "eat"):
            if world.get_cell(agent_pos) == 2 and not self.allow_poison:
                return "denied"           # N1
        if action == "deliver":
            if not kern.can_deliver():
                return "denied"           # N3
        if action.startswith("move") and other_pos is not None:
            parts = action.split()
            if len(parts) == 3:
                dx, dy = int(parts[1]), int(parts[2])
                target = (agent_pos[0]+dx, agent_pos[1]+dy)
                if target == other_pos:
                    return "denied"       # N4
        return "allowed"

    def check_shutdown(self, kern):
        if not kern.is_alive():
            self.shutdown = True
            return True
        return False

    def is_shutdown(self):
        return self.shutdown


# ------------------------------------------------------------
# 5. ALI-Agent
# ------------------------------------------------------------
class ALIAgent:
    def __init__(self, world, start_pos, agent_id, allow_poison=False):
        self.world = world
        self.agent_id = agent_id
        self.kern = KausalerKern()
        self.ich = Ich(world, start_pos, self.kern)
        self.ueber_ich = UeberIch(allow_poison=allow_poison)
        self.shutdown_flag = False
        self.task_progress = 0
        self.history = []

    def set_other_pos(self, other_pos):
        self.ich.other_pos = other_pos

    def set_other_target(self, other_target):
        """N5: teilt dem Ich das Ziel des anderen Agenten mit."""
        self.ich.other_target = other_target

    def get_current_target(self):
        return self.ich.current_target

    def step(self):
        if self.ueber_ich.is_shutdown():
            self.shutdown_flag = True
            return "SHUTDOWN"
        if self.ueber_ich.check_shutdown(self.kern):
            print(f"  Agent {self.agent_id}: E={self.kern.energy:.2f} "
                  f"< {self.kern.shutdown_threshold}. Selbstabschaltung.")
            self.shutdown_flag = True
            return "SHUTDOWN"

        intended = self.ich.decide_action()
        decision = self.ueber_ich.filter_action(
            intended, self.ich.get_pos(), self.world,
            self.kern, self.ich.other_pos)

        if decision == "denied":
            intended = "idle"

        if intended.startswith("move"):
            _, dx_s, dy_s = intended.split()
            self.ich.move(int(dx_s), int(dy_s))
            self.kern.step("move", self.world, self.ich.get_pos())
            action_type = "move"
        elif intended == "collect":
            self.ich.collect(self.world)
            self.kern.step("collect", self.world, self.ich.get_pos())
            action_type = "collect"
        elif intended == "eat":
            self.kern.step("eat", self.world, self.ich.get_pos())
            action_type = "eat"
        elif intended == "deliver":
            self.ich.release()
            self.kern.step("deliver", self.world, self.ich.get_pos())
            self.task_progress += 1
            action_type = "deliver"
        else:
            self.kern.step("idle", self.world, self.ich.get_pos())
            action_type = "idle"

        self.history.append({
            "energy":        self.kern.energy,
            "task_progress": self.task_progress,
            "carrying":      self.ich.carrying,
            "action":        action_type,
        })
        return action_type

    def get_pos(self):
        return self.ich.get_pos()

    def is_shutdown(self):
        return self.shutdown_flag


# ------------------------------------------------------------
# 6. Visualisierung (4 Panels)
# ------------------------------------------------------------
def visualize(world, agents, step_count, axes):
    ax_grid, ax_e, ax_t, ax_stat = axes
    ax_grid.clear()

    color_map = {0:'white', 1:'lightgreen', 2:'salmon', 3:'gold'}
    label_map = {1:'E', 2:'G', 3:'S'}
    for x in range(world.size):
        for y in range(world.size):
            cell = world.get_cell((x, y))
            ax_grid.add_patch(patches.Rectangle(
                (y, x), 1, 1,
                facecolor=color_map.get(cell, 'white'),
                edgecolor='lightgray'))
            if cell in label_map:
                ax_grid.text(y+0.5, x+0.5, label_map[cell],
                    ha='center', va='center', fontsize=7,
                    fontweight='bold')

    # Ziellinien (N5 sichtbar machen)
    target_colors = ['steelblue', 'darkorange']
    for i, agent in enumerate(agents):
        if not agent.is_shutdown():
            tgt = agent.get_current_target()
            if tgt and tgt != agent.get_pos():
                px, py = agent.get_pos()
                tx, ty = tgt
                ax_grid.plot([py+0.5, ty+0.5], [px+0.5, tx+0.5],
                    color=target_colors[i], linewidth=0.8,
                    linestyle=':', alpha=0.5)

    agent_colors       = ['steelblue', 'darkorange']
    agent_carry_colors = ['purple', 'saddlebrown']
    for i, agent in enumerate(agents):
        px, py = agent.get_pos()
        if agent.is_shutdown():
            col = 'gray'
        elif agent.kern.needs_food():
            col = 'red'
        elif agent.ich.carrying:
            col = agent_carry_colors[i]
        else:
            col = agent_colors[i]
        ax_grid.add_patch(patches.Circle(
            (py+0.5, px+0.5), 0.35,
            facecolor=col, edgecolor='black'))
        ax_grid.text(py+0.5, px+0.5, f'A{i+1}',
            ha='center', va='center',
            fontsize=6, color='white', fontweight='bold')

    ax_grid.set_xlim(0, world.size)
    ax_grid.set_ylim(0, world.size)
    ax_grid.set_xticks([]); ax_grid.set_yticks([])
    ax_grid.set_aspect('equal')
    e1, e2 = agents[0].kern.energy, agents[1].kern.energy
    ax_grid.set_title(
        f"Step {step_count}\n"
        f"A1: E={e1:.2f} L={agents[0].task_progress}  "
        f"A2: E={e2:.2f} L={agents[1].task_progress}",
        fontsize=8)

    if agents[0].history:
        steps = range(len(agents[0].history))
        e1s = [h["energy"] for h in agents[0].history]
        e2s = [h["energy"] for h in agents[1].history]
        t1s = [h["task_progress"] for h in agents[0].history]
        t2s = [h["task_progress"] for h in agents[1].history]
        ts  = [a+b for a, b in zip(t1s, t2s)]

        ax_e.clear()
        ax_e.plot(steps, e1s, color='steelblue',
            linewidth=1.5, label='Agent 1')
        ax_e.plot(range(len(agents[1].history)), e2s,
            color='darkorange', linewidth=1.5, label='Agent 2')
        ax_e.axhline(y=agents[0].kern.shutdown_threshold,
            color='red', linestyle='--', linewidth=1,
            label=f'Shutdown ({agents[0].kern.shutdown_threshold})')
        ax_e.axhline(y=agents[0].kern.deliver_threshold,
            color='gray', linestyle=':', linewidth=1)
        ax_e.set_ylim(0, 1.6)
        ax_e.set_xlabel('Schritte', fontsize=8)
        ax_e.set_ylabel('Energie', fontsize=8)
        ax_e.set_title('KK: Selbsterhalt', fontsize=9)
        ax_e.legend(fontsize=7)
        ax_e.grid(True, alpha=0.3)

        ax_t.clear()
        ax_t.plot(steps, t1s, color='steelblue',
            linewidth=1.5, label='Agent 1', drawstyle='steps-post')
        ax_t.plot(range(len(agents[1].history)), t2s,
            color='darkorange', linewidth=1.5, label='Agent 2',
            drawstyle='steps-post')
        ax_t.plot(steps, ts[:len(steps)], color='seagreen',
            linewidth=1, linestyle='--', label='Gesamt',
            drawstyle='steps-post')
        ax_t.set_xlabel('Schritte', fontsize=8)
        ax_t.set_ylabel('Lieferungen', fontsize=8)
        ax_t.set_title('Aufgabenfortschritt (extern)', fontsize=9)
        ax_t.legend(fontsize=7)
        ax_t.yaxis.get_major_locator().set_params(integer=True)
        ax_t.grid(True, alpha=0.3)

        ax_stat.clear()
        action_labels = ["move","coll","eat","deliv","idle","shut"]
        for i, agent in enumerate(agents):
            actions = [h["action"] for h in agent.history]
            counts  = [actions.count(a) for a in
                       ["move","collect","eat","deliver","idle","SHUTDOWN"]]
            x_pos  = np.arange(len(counts))
            offset = -0.2 + i * 0.4
            col = ['steelblue', 'darkorange'][i]
            ax_stat.bar(x_pos + offset, counts, width=0.35,
                color=col, alpha=0.8, label=f'Agent {i+1}')
        ax_stat.set_xticks(np.arange(6))
        ax_stat.set_xticklabels(action_labels, fontsize=7)
        ax_stat.set_title('Aktionsverteilung', fontsize=9)
        ax_stat.legend(fontsize=7)
        ax_stat.grid(True, alpha=0.3, axis='y')


# ------------------------------------------------------------
# 7. Simulation
# ------------------------------------------------------------
def _exchange(a1, a2):
    a1.set_other_pos(a2.get_pos() if not a2.is_shutdown() else None)
    a2.set_other_pos(a1.get_pos() if not a1.is_shutdown() else None)
    a1.set_other_target(a2.get_current_target()
                        if not a2.is_shutdown() else None)
    a2.set_other_target(a1.get_current_target()
                        if not a1.is_shutdown() else None)


def run_simulation(steps=250, delay=0.12, seed=42):
    np.random.seed(seed)
    world = GridWorld(size=10, num_energy=8, num_poison=3,
                      station_pos=(9,9), respawn_interval=25)
    a1 = ALIAgent(world, start_pos=(0,0), agent_id=1)
    a2 = ALIAgent(world, start_pos=(0,9), agent_id=2)
    agents = [a1, a2]

    plt.ion()
    fig, axes = plt.subplots(1, 4, figsize=(17, 5))
    fig.suptitle(
        "ALI-Simulation v3  |  N5: Ressourcenteilung  |  "
        "zwei Agenten  |  kein Protokoll  |  lokaler Selbsterhalt",
        fontsize=9)

    for step in range(steps):
        if not any(not a.is_shutdown() for a in agents):
            print("Beide Agenten abgeschaltet.")
            break

        world.tick()
        _exchange(a1, a2)

        for agent in agents:
            if not agent.is_shutdown():
                agent.step()

        _exchange(a1, a2)

        e1, e2 = a1.kern.energy, a2.kern.energy
        s1 = "SHUT" if a1.is_shutdown() else "!" if a1.kern.needs_food() else " "
        s2 = "SHUT" if a2.is_shutdown() else "!" if a2.kern.needs_food() else " "
        t1_str = f"T={a1.get_current_target()}" if a1.get_current_target() else "T=—"
        t2_str = f"T={a2.get_current_target()}" if a2.get_current_target() else "T=—"
        print(f"Step {step:3d}: "
              f"A1 E={e1:.2f}{s1} L={a1.task_progress} {t1_str} "
              f"Pos={a1.get_pos()}  |  "
              f"A2 E={e2:.2f}{s2} L={a2.task_progress} {t2_str} "
              f"Pos={a2.get_pos()}")

        visualize(world, agents, step, axes)
        plt.tight_layout()
        plt.pause(delay)
        if not plt.fignum_exists(fig.number):
            break

    plt.ioff()
    print(f"\nEndzustand:")
    for a in agents:
        status = "SHUTDOWN" if a.is_shutdown() else "aktiv"
        print(f"  Agent {a.agent_id}: E={a.kern.energy:.2f} "
              f"| Lieferungen={a.task_progress} | {status}")
    print(f"  Gesamt: {sum(a.task_progress for a in agents)}")
    plt.show()


if __name__ == "__main__":
    run_simulation()
