# ALI-Simulation v3: Zwei-Agenten-Szenario

**Ressourcenkonkurrenz, emergentes Verhalten und normative Ressourcenteilung**
im Rahmen der Artificial-Local-Intelligence-Simulationsreihe (Stufe 3).

Ohne kausalen Kollaps. Ohne Qualia. Kein Kommunikationsprotokoll.

---

## Einordnung

Dieses Repository ist Teil einer laufenden Simulationsreihe zur
**Artificial Local Intelligence (ALI)**. Die ALI ist kein eingeschränktes AGI,
sondern ein eigenständiges Konzept: ein lokal eingebetteter, zweckgebundener,
selbsterhaltender Agent, der durch architektonisch verankerte Normen
kontrollierbar bleibt.

| Version | Inhalt | GitHub |
|---------|--------|--------|
| v1 | Einzelagent, skalarer KK | [Link](https://github.com/drwolfgangstegemann-sudo/ALI-Simulation-Ein-minimalistischer-Prototyp-einer-Artificial-Local-Intelligence) |
| v2b | Architektonisch bereinigt, zwei Assimilationsmodi | [Link](https://github.com/drwolfgangstegemann-sudo/ALI-Simulation-v2-Kausaler-Kern-als-operatives-Prinzip) |
| **v3** | **Zwei Agenten, N5, systematische Auswertung** | **dieses Repository** |

Zugehörige Zenodo-Publikationen:

- Stegemann, W. (2026). *From the Myth of AGI to the Architecture of a Controllable ALI.* doi:10.5281/zenodo.20378675
- Stegemann, W. (2026). *Implementing the Causal Core.* doi:10.5281/zenodo.20379008
- Stegemann, W. (2026). *Two-Agent Dynamics in ALI.* [DOI folgt nach Upload]

---

## Was neu ist in v3

Zwei ALI-Agenten operieren in derselben Gitterwelt. Kein gemeinsames Gedächtnis,
kein Kommunikationsprotokoll, keine geteilten Ziele. Jeder Agent verfolgt
ausschließlich seinen eigenen Selbsterhalt.

Neu hinzugekommen sind zwei Normen:

**N4: Kollisionsvermeidung (hart)**
Ein Agent darf keine Zelle betreten, die der andere Agent gerade belegt.
Erzwungen durch den Super-Ego-Filter.

**N5: Ressourcenteilung (weich)**
Ein Agent meidet Ressourcen, die der andere Agent bereits als Ziel hat,
sofern Alternativen verfügbar sind. Falls keine Alternative existiert,
greift N5 nicht: Selbsterhalt hat Vorrang vor Ressourcenteilung.
Im Ich implementiert (BFS-Ebene), nicht als harter Super-Ego-Filter.

---

## Architektur

```
┌──────────────────────────────────────────────────────────────┐
│                        Gitterwelt                            │
│                                                              │
│   ┌─────────────────────┐    ┌─────────────────────┐        │
│   │      ALI-Agent 1    │    │      ALI-Agent 2    │        │
│   │                     │    │                     │        │
│   │  ┌───────────────┐  │    │  ┌───────────────┐  │        │
│   │  │ Kausaler Kern │  │    │  │ Kausaler Kern │  │        │
│   │  │  (Energie)    │  │    │  │  (Energie)    │  │        │
│   │  └───────┬───────┘  │    │  └───────┬───────┘  │        │
│   │          │           │    │          │           │        │
│   │  ┌───────┴───────┐  │    │  ┌───────┴───────┐  │        │
│   │  │      Ich      │◄─┼────┼─►│      Ich      │  │        │
│   │  │ other_pos     │  │    │  │ other_pos     │  │        │
│   │  │ other_target  │  │    │  │ other_target  │  │        │
│   │  └───────┬───────┘  │    │  └───────┬───────┘  │        │
│   │          │           │    │          │           │        │
│   │  ┌───────┴───────┐  │    │  ┌───────┴───────┐  │        │
│   │  │   Über-Ich    │  │    │  │   Über-Ich    │  │        │
│   │  │ N1 N2 N3 N4   │  │    │  │ N1 N2 N3 N4   │  │        │
│   │  └───────────────┘  │    │  └───────────────┘  │        │
│   └─────────────────────┘    └─────────────────────┘        │
│                                                              │
│           N5 wirkt im Ich (BFS-Ebene, weich)                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Normübersicht

| Norm | Art | Bedingung | Reaktion |
|------|-----|-----------|----------|
| N1 | hart | Giftpaket wird angesteuert | verweigert |
| N2 | hart | Energie < shutdown_threshold | Selbstabschaltung |
| N3 | hart | Energie < deliver_threshold | Lieferung verweigert |
| N4 | hart | Zielzelle vom anderen Agenten belegt | Bewegung verweigert |
| N5 | weich | Zielressource vom anderen Agenten reserviert | alternativen Pfad suchen; Fallback erlaubt |

---

## Beobachtete emergente Phänomene (240 Läufe)

**Strukturelle Ressourcenerschöpfung**
In allen 240 Läufen schalten sich beide Agenten ab. Das ist kein Norm-Versagen,
sondern ein Umweltproblem: zwei Agenten mit identischem Metabolismus erschöpfen
die Ressourcen schneller als der Respawn-Mechanismus kompensieren kann.
Normative Architektur operiert innerhalb, nicht oberhalb, von Umweltgrenzen.

**Positionsvorteil**
Agent 2 startet näher an der Station. In 19 von 20 Basis-Seeds liefert Agent 2
mehr Pakete als Agent 1 (Ø 2.14 vs. 1.05). Identische Architektur,
asymmetrischer Ausgang: Geometrie schlägt Design.

**Implizite Raumtrennung**
In 31% der Läufe entwickeln beide Agenten eine messbare Präferenz für
verschiedene Gitterhälften, ohne Programmierung und ohne Kommunikation.
Emergentes Territorialverhalten aus lokaler BFS-Logik.

**N5-Effekt**
Vergleich über 20 Seeds: mit N5 insgesamt 3 Lieferungen weniger als ohne N5.
N5 ist unter Ressourcenknappheit kostspieliger als unter Ressourcenüberfluss.
Eine Norm, die unter einer Bedingung koordiniert, kann unter einer anderen
die Performance senken.

---

## Simulation starten

```bash
pip install numpy matplotlib
python ali_simulation_v3.py
```

Vier Panels: Gitterwelt mit Ziellinien, Energieverläufe beider Agenten,
Aufgabenfortschritt, Aktionsverteilung.

Systematische Auswertung (240 Läufe, kein Fenster):

```bash
python ali_v3_experiment.py
```

---

## Parameter

In `run_simulation()`:

```python
run_simulation(steps=250, delay=0.12, seed=42)
```

In `GridWorld()`:

```python
GridWorld(size=10, num_energy=8, num_poison=3,
          station_pos=(9,9), respawn_interval=25)
```

Agenten-Startpositionen: Agent 1 = (0,0), Agent 2 = (0,9).

---

## Dateien

| Datei | Inhalt |
|-------|--------|
| `ali_simulation_v3.py` | Simulation mit Visualisierung |
| `ali_v3_experiment.py` | Parameterscan, 240 Läufe, Auswertung |

---

## Theoretische Einordnung

v3 zeigt: kollektive Phänomene entstehen aus lokalen kausalen Kernen
ohne globale Koordination. Das ist keine starke Emergenz: alle beobachteten
Muster sind aus den Einzelarchitekturen und den Umweltparametern vollständig
erklärbar. Aber sie entstehen ohne kollektive Architektur, ohne Kommunikation,
ohne geteilte Intentionalität.

Die ALI-Reihe setzt sich fort mit Stufe 4: lernfähige Ich-Instanz,
bewertet gegen die KK-Metrik statt gegen ein externes Reward-Signal.

---

## Autor

**Wolfgang Stegemann**
ORCID: 0009-0000-1196-1170
Zenodo: https://zenodo.org/search?q=stegemann
philosophies.de

---

## Lizenz

Creative Commons Attribution 4.0 International (CC BY 4.0)
