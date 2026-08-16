<!--
═══════════════════════════════════════════════════════════════════════
  PROTECTED KNOWLEDGE FILE — DO NOT MODIFY WITHOUT OWNER APPROVAL
  Owner: Amit Swisa
  Status: commercial + architectural decisions
  Agents: READ before proposing features, refactors, or "improvements".
          If a task is not in the current phase, say so instead of doing it.
          You MAY append to "Change log" and "Decision log".
          You MAY NOT change phases, pricing, or the service/SaaS decision.
═══════════════════════════════════════════════════════════════════════
-->

# Product strategy — from one gym to a repeatable offering

**Companion files:** `CLIENT_IDAN.md` (who and why) · `DATA_INVENTORY.md` (what the data is)

---

## 1. The decision

> **Service-first, SaaS-shaped.**
>
> Run the pipeline **for** the gym as a paid weekly/monthly service.
> Build every component as if it will become software — but do not build the
> software until a second paying gym exists.

### Why not SaaS immediately

| Reason | Evidence |
|---|---|
| **n = 1** | One customer. Any abstraction now is a guess about gym #2. |
| **Time-per-close is unknown** | Never measured. You cannot price or automate an unmeasured process. |
| **The customer's machine is the risk** | Idan's local agent produced `גרסה 2` with inverted income signs. That is exactly the failure a hosted product is supposed to prevent — and it already happened. |
| **The output format is unstable** | The budget workbook reshapes monthly (`DATA_INVENTORY.md` §5). Shipping a UI on top of a moving target multiplies the maintenance cost. |
| **Cash timing** | A retainer bills in weeks. A SaaS bills in quarters, after build + onboarding + trust. |

### Why not pure service forever

The file inventory found a **clean seam**: four inputs are raw system exports
(Priority, Hilan, Arbox, PDFs) and behave the same at any gym using those
systems. Three outputs are Idan's personal Excel craft.

That means the product is real — but it lives on the **input** side, and on
**owning the output**, not on maintaining his workbooks.

### What "SaaS-shaped" means in practice

1. Parse **raw exports**, never hand-built workbooks, wherever there is a choice
2. Emit **our own** deliverable; do not write into the client's file
3. Everything client-specific lives in **config**, never in code
4. Every run produces a **manifest** (inputs, hashes, config version, decisions)
5. Approvals are **explicit and recorded**, not implicit in a spreadsheet colour

Do those five things while delivering a service, and the eventual web app is a
UI over an existing engine — not a rewrite.

---

## 2. What the POC proved and did not prove

### Proved ✅
- The money math is correct (96 tests; YTD reconciles against real data)
- Hebrew file discovery works without exact filenames
- A non-technical user can trigger it
- The domain is painful and the value is real — **≥3.5 h/week saved**, his words
- Flag-based review (`דגלים`) is a workable interaction model

### Not proved ❌
| Gap | Evidence |
|---|---|
| Re-run safety | Manual value `999` written → re-run → came back `None` |
| Multi-month | `--month 7` produced a workbook with no June block at all |
| Year rollover | Hard `KeyError` on a 2027 tab; `2026` hardcoded in 5 files |
| Failure visibility | `run_all.py` always exits `0` — crash and success look identical |
| Source selection | 4 ledger tabs, ~₪240k spread, silent choice |
| Controls actually running | Hilan check dead; `דגלים` shows a false all-clear |
| Deliverable preservation | Filenames carry no month; July overwrites June; `output/` is gitignored |
| Generalization | `branches.json` hardcodes row numbers and one month's signed totals |

### The three assumptions that would hurt most if wrong

1. **`התאמה ידנית` exists** — it does not appear in his files (`DATA_INVENTORY.md` §5)
2. **Monthly cadence** — he said weekly (`CLIENT_IDAN.md` §2)
3. **"Another gym is just config"** — untested; the likeliest failure point in the whole plan

---

## 3. Product surface vs service surface

| Layer | Nature | Strategy |
|---|---|---|
| Priority ledger · Hilan · Arbox · invoice PDFs | Raw exports, stable shape | **Productize.** Parsers, validation, mapping. |
| Chart-of-accounts mapping | Per-client data | **Configure.** Never hardcode. |
| `חיוב יזם` interface (`מס סעיף \| שם סעיף \| סכום \| הערות`) | Small, coded, tabular | **Standardize on this contract.** |
| Budget workbook · דוח מרכז · מס"ב tabs | Hand-built, mutating | **Replace over time.** Do not maintain. |
| Budget balancing · approvals · sign-off | Human judgement | **Never automate.** |

---

## 4. Operating model

```
Gym sends files  →  YOU run the pipeline  →  Agent drafts the summary
                                                    ↓
                                          YOU review and approve
                                                    ↓
                                    Gym receives workbook + Hebrew summary
                                                    ↓
                                      Gym approves flagged decisions
```

**The customer does not run the agent.** That single decision eliminates: agent
drift on their machine, their Python environment, their API keys, their
misreading of a traceback, and every repeat of the `גרסה 2` incident.

### Automation boundary

| Automated | Human-approved | Per-gym config |
|---|---|---|
| File intake & recognition | **Unknown trainer / supplier** | Account map |
| Ledger parse & net | **Budget rebalancing** | Sheet bindings |
| Month attribution | **Drift vs target** | Rule order |
| BvA write, signs, rollups, YTD | **Ledger tab choice** | Income code prefixes |
| Flag generation | **Final sign-off** | Targets, rates, terms |
| Draft Hebrew summary | | Recipients, language |

### Where the AI agent belongs

| Good use | Bad use |
|---|---|
| Diagnosing why a number looks wrong | Producing the number |
| Drafting the weekly Hebrew summary | Deciding what is material |
| Proposing an account mapping | Committing it |
| Improving the engine between runs | Hand-editing the deliverable |
| Triaging flags: routine vs needs-Idan | Clearing a flag |

> **Structural rule:** the agent may change the *engine*; it may never
> hand-produce the *money output*. This is enforced in `AGENTS.md` and `SKILL.md`.

---

## 5. Phased roadmap

### Phase 0 — Safety fixes · *before the next delivery*

**Objective:** stop producing plausible-but-wrong output.

| | |
|---|---|
| **Deliverables** | Manual layer survives re-runs · exit codes propagate · Hilan control fixed · ledger tab explicit and logged · month + run-id in filenames · swallowed exceptions become hard flags |
| **Success** | Re-run twice → manual value intact · force a failure → non-zero exit · two different tabs → different, *logged*, result |
| **Risk** | Fixing intake may shift historical numbers — snapshot current output first for comparison |
| **Gate** | One clean cycle with zero silent failures |

### Phase 1 — Evidence layer · *pilot-ready*

**Objective:** make the output defensible to someone who was not in the room.

| | |
|---|---|
| **Deliverables** | Run manifest (inputs, hashes, tab used, config version, timestamp) · week-over-week diff · one-page Hebrew summary · ledger↔BvA tie-out · unmapped accounts surfaced to the client · explicit approval checkpoint |
| **Success** | Idan answers *"why is this number what it is?"* without calling you |
| **Risk** | Scope creep into reporting. Hold the line at one page + one manifest. |
| **Gate** | Idan (or his accountant) accepts the pack with no follow-up call |

### Phase 2 — First paid pilot · *3 months, Idan*

**Objective:** prove the service is repeatable, priced, and profitable.

| | |
|---|---|
| **Deliverables** | Signed scope · fixed weekly calendar · SLA (delivery day, question turnaround) · **measured time-per-cycle** · 3 consecutive clean months |
| **Success** | Weekly cycle in **< 30 min** of your time · monthly close in **< 2 h** · no emergency escalations · invoiced twice, paid twice |
| **Risk** | Time does not drop → the price is wrong or the automation is insufficient. **Measure this above everything else.** |
| **Gate** | 3 months delivered on schedule + Idan agrees to a reference call |

### Phase 3 — Second gym · *the generalization test*

**Objective:** find out what is genuinely product versus bespoke.

| | |
|---|---|
| **Deliverables** | Per-gym config isolation · label-based sheet binding (no row indexes) · onboarding checklist with measured hours · year-rollover fixed |
| **Success** | Gym #2 onboarded in **< 2 days**, **zero engine forks** |
| **Risk** | A different chart of accounts forces a rewrite. **This is the highest-risk moment in the plan.** Discover it at gym #2, not gym #5. |
| **Gate** | Two gyms running monthly on **one** codebase |

### Phase 4 — Repeatable offering

**Objective:** sell without bespoke engineering per deal.

| | |
|---|---|
| **Deliverables** | Standard onboarding · templated contract · pricing tiers · client upload portal **only if pull is real** |
| **Gate** | Onboarding cost < one month's fee |

> **Do not start Phase N+1 before the Phase N gate is met.** If an agent proposes
> work from a later phase, the correct response is to name the phase and decline.

---

## 6. Commercial model

### Structure: retainer on the close, not a software licence

| Tier | Scope | Your effort |
|---|---|---|
| **Weekly dashboard** | תקציב מול ביצוע weekly + flags + Hebrew summary | Run + review |
| **Full close** | Weekly, plus monthly billing, suppliers, דוח מרכז reconciliation | + monthly cycle |
| **Close + control** | Full close, plus trainer/supplier chasing, accountant tie-out, trend narrative | + chase loop |
| **Setup** | Onboarding, account mapping, historical backfill | One-time |

**Price on the cycle, not on seats or files.** It matches the customer's mental
model (*"closing the week/month"*) and decouples price from architecture.

### The anchor

Idan's own words: **1 hour → 5 minutes weekly, ≥3.5 h/week saved.**
That is ~14 h/month **on Job 2 alone** — Jobs 1, 3 and 4 are untouched upside.
Use the quote as-is. Do not round it up.

### Standardize vs customize

| Never fork | Config only |
|---|---|
| Two-layer write contract | Chart of accounts |
| Sign conventions | Branch names, sheet bindings |
| Flag categories and severity | Targets, rates, payment terms |
| Run manifest and approval gate | Calendar, recipients |
| Deliverable naming | Summary language |

> **Rule:** a request that requires touching engine logic is either (a) a feature
> for every customer, or (b) declined. **No per-client engine branches.**

### Minimum proof points before selling gym #3

1. Three consecutive clean cycles for Idan, delivered on schedule
2. Time-per-cycle measured and trending **down**
3. Zero silent-failure incidents
4. One written reference from Idan
5. Gym #2 onboarded in ≤ 2 days with **no** engine changes

Selling before #5 means selling a bespoke engagement you will hand-build.

---

## 7. Open questions

Grouped by what they would change. Full list with context in `CLIENT_IDAN.md` §9.

| Area | Question | Changes |
|---|---|---|
| **Workflow** | `התאמה ידנית` or `ביאורים`? | Core safety contract |
| **Workflow** | Weekly or monthly? | Entire delivery rhythm |
| **Workflow** | Memo month vs balance date — which wins? | Money attribution |
| **Data** | Which כרטסת snapshot is authoritative? | ~₪240k of June |
| **Data** | Do other gyms use Priority + Arbox + Hilan? | Whether the product generalizes |
| **Customer** | Idan or the boss holds budget? | Who you sell to |
| **Customer** | Are other gyms warm intros or cold? | Go-to-market cost |
| **Risk** | Is the BvA used externally (bank, franchisor, tax)? | Evidence bar |
| **Risk** | Retention/deletion policy for payroll and tax IDs? | Compliance |
| **Risk** | Who carries the risk of a wrong number reaching the accountant? | Contract terms |
| **Commercial** | Your time budget per cycle before it stops being worth it? | Viability floor |
| **Commercial** | Service revenue or software revenue? | Architecture follows this |

---

## 8. Explicitly out of scope right now

Listed so agents stop proposing them:

- Multi-tenant SaaS infrastructure
- The Next.js web app in `club-finance-recon`
- RAG / Q&A over files
- Staff scheduling (`solver.py`, `scheduler.py` — dead code in this product)
- WhatsApp member bot
- Merging the two repositories
- Outreach to gym #2 before Phase 2's gate

---

## 9. Next 5 actions

| # | Action | Why |
|---|---|---|
| 1 | Ask Idan Q1–Q6 (`CLIENT_IDAN.md` §9) | Two answers invalidate current code assumptions |
| 2 | Fix manual-layer loss, silent failures, ledger-tab ambiguity | Blocking safety defects |
| 3 | Run one **weekly** cycle end-to-end yourself, timed | Validates real cadence, produces the hours number |
| 4 | Decide: write into his workbook, or emit our own | Determines whether SaaS is 3 months or 12 months away |
| 5 | Draft the retainer scope on the weekly cycle | Converts a POC into a priced offer |

---

## Decision log

Append only. One line per decision, with the reason.

| Date | Decision | Reason |
|------|----------|--------|
| 2026-07-31 | Service-first, SaaS-shaped | n=1, unmeasured effort, unstable output format, customer-machine risk already realized |
| 2026-07-31 | Customer does not run the agent | `גרסה 2` incident |
| 2026-07-31 | Standardize on `חיוב יזם` as the interface contract | Small, account-coded, stable — unlike the workbooks around it |
| 2026-07-31 | Web app parked until gym #2 signs | Avoids building a UI over a moving target |

## Change log

| Date | Who | Change |
|------|-----|--------|
| 2026-07-31 | Amit + agent | Created from gap analysis, file inventory, and client transcript |
