# Product scope — gym-recon

## Client

**אריאל פיט & ספא בע"מ** (A+ Street Mall) — חדר כושר + פילאטיס.  
Operational owner for monthly close / budget-vs-actual review: **Idan**.

## What this repository is

A **Python CLI finance engine** plus an **agent-operated** monthly workflow.

- **Engine:** turns monthly source files into validated Excel deliverables with stable money rules.  
- **Agent:** judges what is wrong, what should change, how to change it, and which tools to run — then implements code/config when rules need to evolve.

| For Idan | How |
|----------|-----|
| Official **תקציב מול ביצוע** (club + Pilates) from accounting ledger | `tools/ledger_sync.py` |
| Trainer invoice control + flags | `tools/billing.py` |
| Supplier approval pack (+30 / +60) | `tools/suppliers.py` |
| One-shot month | `run_all.py` or `friend_install/run_month.bat` |

Design goals for budget-vs-actual:

- **Overwrite-safe two-layer actuals** (system ledger / manager manual / display sum)
- **Rerunnable** every month without wiping manager adjustments
- **Trustworthy money path** — amounts come from code, not freestyle chat Excel
- Clear audit: footer `written by gym-recon ledger_sync`
- **Agent autonomy** on diagnosis, prioritization, and engineering changes (see `AGENTS.md`)

## What this repository is not

- Not a web dashboard or Tkinter GUI (that lives in `club-finance-recon`)
- Not a freestyle Excel sandbox for one-off money workbooks
- Not a place to store client PDFs/amounts in git (`input/` / `output/` stay local)
- Not “agent may only press the same button forever” — agents **decide and improve** within product rules

## Related repository

| Repo | Role for the same client |
|------|---------------------------|
| **This (`gym-recon`)** | Official ledger → תקציב מול ביצוע + CLI billing/suppliers |
| [`club-finance-recon`](https://github.com/amitswsisa-cyber/club-finance-recon) | Trainer recon reports, HTML dashboard, GUI, **draft** Excel packs |

Same business; **different pipelines and output contracts.** Use this repo when Idan needs engine BvA or CLI billing.
