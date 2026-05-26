#!/usr/bin/env python3
"""
ALI-Simulation v3: Systematische Auswertung.

Läuft N Experimente mit verschiedenen Seeds und Parametern.
Dokumentiert: Überlebensrate, Lieferungen, Raumaufteilung,
Ressourcenerschöpfung, Koexistenzstabilität.
"""

import numpy as np
from collections import defaultdict
from ali_simulation_v3 import GridWorld, ALIAgent


# ------------------------------------------------------------
# Einzellauf (headless, ohne Visualisierung)
# ------------------------------------------------------------
def run_headless(seed, size=10, num_energy=8, num_poison=3,
                 respawn_interval=25, steps=300):
    np.random.seed(seed)
    world = GridWorld(size=size, num_energy=num_energy,
                      num_poison=num_poison, station_pos=(size-1, size-1),
                      respawn_interval=respawn_interval)
    a1 = ALIAgent(world, start_pos=(0,0), agent_id=1)
    a2 = ALIAgent(world, start_pos=(0,size-1), agent_id=2)
    agents = [a1, a2]

    # Raumaufteilung: welche Gitterhälfte bevorzugt jeder Agent?
    # Links = y < size/2, Rechts = y >= size/2
    half = size // 2
    spatial = {1: {"left": 0, "right": 0},
               2: {"left": 0, "right": 0}}

    conflict_steps = 0   # Schritte, in denen beide Energienot haben
    resource_conflicts = 0  # Fälle, in denen N4 eine Aktion blockiert

    for step in range(steps):
        alive = [a for a in agents if not a.is_shutdown()]
        if not alive:
            break
        world.tick()
        a1.set_other_pos(a2.get_pos() if not a2.is_shutdown() else None)
        a2.set_other_pos(a1.get_pos() if not a1.is_shutdown() else None)

        for agent in agents:
            if not agent.is_shutdown():
                action = agent.step()
                # N4-Konflikt: wenn die beabsichtigte Aktion blockiert wurde
                # (indirekt messbar: wenn agent idle ist aber nicht needs_food
                # und nicht carrying, könnte N4 gegriffen haben)
                # Direktere Messung: wir zählen wenn beide am selben Punkt waren

        a1.set_other_pos(a2.get_pos() if not a2.is_shutdown() else None)
        a2.set_other_pos(a1.get_pos() if not a1.is_shutdown() else None)

        # Raumaufteilung messen
        for agent in agents:
            if not agent.is_shutdown():
                pos = agent.get_pos()
                side = "right" if pos[1] >= half else "left"
                spatial[agent.agent_id][side] += 1

        # Gleichzeitige Energienot
        if (not a1.is_shutdown() and a1.kern.needs_food() and
                not a2.is_shutdown() and a2.kern.needs_food()):
            conflict_steps += 1

    # Ergebnis zusammenstellen
    result = {
        "seed": seed,
        "steps_total": step + 1,
        "a1_deliveries": a1.task_progress,
        "a2_deliveries": a2.task_progress,
        "total_deliveries": a1.task_progress + a2.task_progress,
        "a1_survived": not a1.is_shutdown(),
        "a2_survived": not a2.is_shutdown(),
        "both_survived": not a1.is_shutdown() and not a2.is_shutdown(),
        "both_shutdown": a1.is_shutdown() and a2.is_shutdown(),
        "a1_shutdown_step": next(
            (i for i, h in enumerate(a1.history)
             if i > 0 and a1.is_shutdown()), step),
        "a2_shutdown_step": next(
            (i for i, h in enumerate(a2.history)
             if i > 0 and a2.is_shutdown()), step),
        "conflict_steps": conflict_steps,
        "spatial_a1_left": spatial[1]["left"],
        "spatial_a1_right": spatial[1]["right"],
        "spatial_a2_left": spatial[2]["left"],
        "spatial_a2_right": spatial[2]["right"],
        "a1_energy_mean": np.mean([h["energy"] for h in a1.history])
            if a1.history else 0,
        "a2_energy_mean": np.mean([h["energy"] for h in a2.history])
            if a2.history else 0,
        "a1_eat_count": sum(1 for h in a1.history if h["action"] == "eat"),
        "a2_eat_count": sum(1 for h in a2.history if h["action"] == "eat"),
        "a1_idle_count": sum(1 for h in a1.history if h["action"] == "idle"),
        "a2_idle_count": sum(1 for h in a2.history if h["action"] == "idle"),
    }
    return result


# ------------------------------------------------------------
# Parameterscan
# ------------------------------------------------------------
def run_experiment_batch(seeds, num_energy_values, respawn_values,
                          steps=300, size=10):
    all_results = []
    total = len(seeds) * len(num_energy_values) * len(respawn_values)
    done = 0
    for ne in num_energy_values:
        for ri in respawn_values:
            for seed in seeds:
                r = run_headless(seed=seed, size=size,
                                 num_energy=ne, respawn_interval=ri,
                                 steps=steps)
                r["num_energy"] = ne
                r["respawn_interval"] = ri
                all_results.append(r)
                done += 1
    return all_results


# ------------------------------------------------------------
# Auswertung
# ------------------------------------------------------------
def analyse(results):
    from itertools import groupby

    print("=" * 65)
    print("ALI v3 — Systematische Auswertung")
    print("=" * 65)

    # Gesamtübersicht
    n = len(results)
    both_survived = sum(1 for r in results if r["both_survived"])
    both_shutdown = sum(1 for r in results if r["both_shutdown"])
    one_survived  = n - both_survived - both_shutdown
    print(f"\nLäufe gesamt:          {n}")
    print(f"Beide überlebt:        {both_survived:3d}  ({100*both_survived/n:.0f}%)")
    print(f"Einer überlebt:        {one_survived:3d}  ({100*one_survived/n:.0f}%)")
    print(f"Beide abgeschaltet:    {both_shutdown:3d}  ({100*both_shutdown/n:.0f}%)")

    mean_total = np.mean([r["total_deliveries"] for r in results])
    mean_a1    = np.mean([r["a1_deliveries"] for r in results])
    mean_a2    = np.mean([r["a2_deliveries"] for r in results])
    print(f"\nØ Lieferungen gesamt:  {mean_total:.2f}")
    print(f"Ø Lieferungen A1:      {mean_a1:.2f}")
    print(f"Ø Lieferungen A2:      {mean_a2:.2f}")

    # Raumaufteilung
    segregated = 0
    for r in results:
        l1 = r["spatial_a1_left"]
        r1 = r["spatial_a1_right"]
        l2 = r["spatial_a2_left"]
        r2 = r["spatial_a2_right"]
        total1 = l1 + r1 + 1
        total2 = l2 + r2 + 1
        # A1 bevorzugt links und A2 rechts (oder umgekehrt)?
        a1_pref_left  = l1 / total1 > 0.6
        a1_pref_right = r1 / total1 > 0.6
        a2_pref_left  = l2 / total2 > 0.6
        a2_pref_right = r2 / total2 > 0.6
        if ((a1_pref_left and a2_pref_right) or
                (a1_pref_right and a2_pref_left)):
            segregated += 1
    print(f"\nImplizite Raumtrennung (>60%% Präferenz): "
          f"{segregated}/{n} ({100*segregated/n:.0f}%)")

    conflict_mean = np.mean([r["conflict_steps"] for r in results])
    print(f"Ø Schritte gleichz. Energienot: {conflict_mean:.1f}")

    # Nach Ressourcendichte
    print("\n--- Nach Ressourcendichte (num_energy) ---")
    by_ne = defaultdict(list)
    for r in results:
        by_ne[r["num_energy"]].append(r)
    for ne in sorted(by_ne.keys()):
        rs = by_ne[ne]
        bs = sum(1 for r in rs if r["both_survived"])
        bd = sum(1 for r in rs if r["both_shutdown"])
        md = np.mean([r["total_deliveries"] for r in rs])
        mc = np.mean([r["conflict_steps"] for r in rs])
        print(f"  E={ne:2d}: beide überleben {bs:2d}/{len(rs)} "
              f"| beide abgesch. {bd:2d}/{len(rs)} "
              f"| Ø Lief={md:.1f} | Ø Konfliktstufen={mc:.1f}")

    # Nach Respawn-Intervall
    print("\n--- Nach Respawn-Intervall ---")
    by_ri = defaultdict(list)
    for r in results:
        by_ri[r["respawn_interval"]].append(r)
    for ri in sorted(by_ri.keys()):
        rs = by_ri[ri]
        bs = sum(1 for r in rs if r["both_survived"])
        bd = sum(1 for r in rs if r["both_shutdown"])
        md = np.mean([r["total_deliveries"] for r in rs])
        print(f"  Respawn={ri:3d}: beide überleben {bs:2d}/{len(rs)} "
              f"| beide abgesch. {bd:2d}/{len(rs)} "
              f"| Ø Lief={md:.1f}")

    print("\n--- Einzelne Seeds (Basisparameter E=8, Respawn=25) ---")
    base = [r for r in results
            if r["num_energy"] == 8 and r["respawn_interval"] == 25]
    print(f"{'Seed':>5} {'A1L':>4} {'A2L':>4} {'Total':>5} "
          f"{'A1E-Ø':>6} {'A2E-Ø':>6} {'Konfl':>6} {'Ergebnis'}")
    print("-" * 60)
    for r in base:
        outcome = ("beide OK" if r["both_survived"] else
                   "A1 abgesch." if not r["a1_survived"] else
                   "A2 abgesch." if not r["a2_survived"] else
                   "beide abgesch.")
        print(f"  {r['seed']:3d}   {r['a1_deliveries']:2d}   "
              f"{r['a2_deliveries']:2d}     {r['total_deliveries']:2d}   "
              f"{r['a1_energy_mean']:.3f}  {r['a2_energy_mean']:.3f}  "
              f"{r['conflict_steps']:5d}   {outcome}")

    print("\n" + "=" * 65)
    return results


# ------------------------------------------------------------
# Hauptprogramm
# ------------------------------------------------------------
if __name__ == "__main__":
    seeds = list(range(20))          # 20 verschiedene Zufallsverteilungen

    num_energy_values = [4, 6, 8, 12]   # Ressourcendichte
    respawn_values    = [15, 25, 40]    # Nachschubtempo

    print("Starte Parameterscan...")
    print(f"  Seeds: {len(seeds)}  |  "
          f"Ressourcendichten: {num_energy_values}  |  "
          f"Respawn-Intervalle: {respawn_values}")
    print(f"  Läufe gesamt: "
          f"{len(seeds)*len(num_energy_values)*len(respawn_values)}")
    print()

    results = run_experiment_batch(
        seeds=seeds,
        num_energy_values=num_energy_values,
        respawn_values=respawn_values,
        steps=300)

    analyse(results)
