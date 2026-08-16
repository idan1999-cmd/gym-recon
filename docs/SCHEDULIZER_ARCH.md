# Gym Schedulizer — Architecture Sketch

Nothing built yet. This document is a proposal for workflow #3.

## What it does

The gym manager currently builds the weekly roster by hand — who teaches which class when, at Club or Pilates. Trainers request days off, swap shifts, and preferred time slots. The schedulizer automates this:

1. **Looks at history** from Arbox to understand demand (which classes, which days, how many check-ins)
2. **Solves the puzzle** — assigns trainers to time slots while respecting hard rules (no double-booking, min rest, legal max hours) and soft preferences (trainer X prefers mornings)
3. **Publishes a draft** — Excel workbook the manager can review, tweak, and approve
4. **Handles changes** — swaps, sick days, WhatsApp notifications

## Data flow

```mermaid
flowchart TB
    subgraph Input["📁 Input"]
        A1["Arbox history
        דו\"ח שיעורים.xlsx
        (existing reader)"]
        A2["config/shift_types.json
        Class slots × days × min-max staff"]
        A3["config/trainer_availability.json
        Preferred days, max shifts, days off"]
        A4["config/constraints.json
        Gaps, rest hours, same-room rules"]
    end

    subgraph Core["🧠 Schedulizer Engine"]
        B["demand.py
        Arbox history → demand profile
        Which classes run when?
        Avg check-ins per slot"]
        C["solver.py
        OR-Tools CP-SAT
        Converts rules into math
        Searches for best assignment"]
        D["validator.py
        No conflicts?
        All constraints satisfied?
        Flags for human review"]
    end

    subgraph Output["📤 Output"]
        E["מערכת_משמרות.xlsx
        Draft roster workbook"]
        F["conflicts.json
        Unassignable shifts,
        constraint violations"]
        G["swap_history.json
        Track changes over time"]
    end

    subgraph Live["📱 Live Changes"]
        H["swap.py
        Request swap → check feasibility
        → update roster"]
        I["whatsapp_bridge.py
        Send notifications
        Receive swap replies"]
    end

    Input --> B --> C --> D --> E
    D --> F
    E --> H
    H --> G
    H --> I
```

## New files (proposed)

| File | What it does |
|------|-------------|
| `tools/scheduler.py` | CLI: `--month 7 --draft` or `--publish` — same pattern as `billing.py` |
| `core/demand.py` | Reads Arbox history, builds demand profile: which slots are busy, which are quiet |
| `core/solver.py` | OR-Tools CP-SAT model: decision variables = (trainer × day × slot), constraints = hard + soft, objective = fairness + preference score |
| `core/validator.py` | Post-solve checks: no overlaps, coverage OK, flags anything questionable |
| `core/swap.py` | Swap logic: given current roster, swap A↔B, re-check constraints, produce diff |
| `core/whatsapp_bridge.py` | LangGraph agent that sends "Your shift Tuesday 10:00" and parses "swap me with Dana" |
| `config/shift_types.json` | Template: `{"id":"morning","day":"sunday","start":"08:00","end":"13:00","min_staff":1,"max_staff":2}` |
| `config/trainer_availability.json` | Per trainer: max_shifts_per_week, preferred_days, unavailable_days, preferred_branch |
| `config/constraints.json` | Global: min_gap_between_shifts (hours), max_consecutive_days, rest_after_evening |

## How OR-Tools CP-SAT fits (plain language)

The gym roster is a **constraint satisfaction problem**. You have:
- **Variables:** which trainer teaches each slot
- **Domain:** the list of available trainers
- **Hard constraints:** a trainer can't be in two places, can't work 7 days straight, must rest 12h after evening shift
- **Soft constraints:** trainer prefers mornings, prefers Club over Pilates
- **Objective:** maximize preference satisfaction while meeting all hard rules

OR-Tools CP-SAT is the engine that finds a solution faster than trial-and-error. It's used by every major scheduling app (Nurse Rostering, retail shifts, airline crew). Free, open-source, works in Python, handles hundreds of trainers and thousands of slots.

The gym case is small (<30 trainers, <50 slots/week) — OR-Tools will solve it in milliseconds.

## Integration with existing gym-recon

| Existing piece | How schedulizer uses it |
|----------------|------------------------|
| `core/arbox.py` | Tells us **what classes** ran historically, **which trainers** taught them, **average check-ins** per slot → demand profile |
| `config/trainer_aliases.json` | Already maps trainer names → canonical IDs; schedulizer shares same trainer list |
| `config/branches.json` | Club vs Pilates — scheduler needs branch-level slots |
| `openpyxl` | Same Excel library for roster output workbook |
| `tools/` pattern | `scheduler.py` follows the same CLI convention as `billing.py` — argparse, main(), pytest tests |

## What it does NOT do (yet)

- No real-time scheduling (it produces a draft for the week/month, not live adjustments)
- No WhatsApp integration yet — that's a separate workflow (#4)
- No automatic publication — manager always reviews the draft

## Next: Let's talk about it

Read this, then tell me what's wrong, what's missing, or what you want to change. When you're happy, I can:

- **Option A:** Build `config/shift_types.json` + `core/demand.py` as a standalone reader — no OR-Tools yet, just see what Arbox history looks like as demand
- **Option B:** Scaffold `tools/scheduler.py` + `core/solver.py` with a tiny 2-trainer 2-slot example so you see OR-Tools run end-to-end
- **Option C:** Write a plain-language comparison of Perplexity SaaS (7shifts, When I Work) vs OR-Tools approach
