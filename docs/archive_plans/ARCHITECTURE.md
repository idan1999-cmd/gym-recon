# Gym Recon Architecture

```mermaid
flowchart TB
    subgraph Input["📁 Input Folder (input/)"]
        A1["כרטסת Ledger"]
        A2["תקציב מול ביצוע Budget"]
        A3['דו"ח שיעורים Arbox']
        A4["דוח מרכז לאישור מנהל (per branch)"]
        A5["invoices/ (PDFs or OCR JSON)"]
    end

    subgraph Core["🧠 Core Engine (core/)"]
        B["inputs.py
        Auto-detect by content
        Preflight check"]
        C["ocr.py
        Agent vision (default)
        Gemini fallback (headless)"]
        D["ledger.py
        Parse ledger
        Monthly movement"]
        E["arbox.py
        Load sessions
        Alias resolution"]
        F["common.py
        Aliases, pay matrix
        Trainer resolution"]
    end

    subgraph Jobs["⚙️ Jobs (jobs/)"]
        subgraph LedgerSync["Job 1: Ledger Sync"]
            G["ledger_output.py
            Map accounts (180/181)
            Two-layer block:
            ביצוע(כרטסת) + התאמה ידנית
            = ביצוע (as VALUE)"]
        end

        subgraph Billing["Job 2: Trainer Billing"]
            H["job_billing.py
            Phase A: Validate each invoice
            Three-way match:
            Invoice × Arbox × Rate
            Hilan hours check"]
            I["audit.py
            Verdict engine:
            OK / REVIEW / BLOCK"]
            J["billing_output.py
            Phase B: Write to דוח מרכז
            Resolve חיוב יזם to values
            Produce דגלים flags"]
        end
    end

    subgraph Output["📤 Output (output/)"]
        K["תקציב_מול_ביצוע_חדר_כושר.xlsx
        תקציב_מול_ביצוע_פילאטיס.xlsx"]
        L["חיוב_חדר_כושר.xlsx
        חיוב_פילאטיס.xlsx
        (with דגלים flags sheet)"]
        M["trainer_amounts_*.json
        pending_trainers_*.json
        audit_log.json"]
    end

    subgraph PostCheck["🔍 Optional Post-Validate"]
        N["officecli_bridge.py
        Calls officecli validate
        on each output .xlsx"]
    end

    Input --> B
    B --> C & D & E & F
    D --> LedgerSync
    E --> Billing
    F --> Billing
    C --> Billing
    B --> LedgerSync & Billing
    LedgerSync --> K
    Billing --> L
    Billing --> M
    K & L --> N

    style Input fill:#e8f5e9,stroke:#2e7d32
    style Core fill:#e3f2fd,stroke:#1565c0
    style Jobs fill:#fff3e0,stroke:#e65100
    style Output fill:#f3e5f5,stroke:#6a1b9a
    style PostCheck fill:#fff8e1,stroke:#f9a825
```

## Flow summary

1. **Core** detects input files by content (not filenames)
2. **Ledger Sync** reads ledger → computes monthly movement → writes into budget template (safe two-layer: system + manual)
3. **Billing** reads invoices (via agent vision or Gemini) → three-way match vs Arbox sessions vs agreed rate → Hilan hours check → writes validated amounts into approval workbook → resolves formulas to values → flags everything uncertain in דגלים
4. **Post-check** runs `officecli validate` on output files (optional, never crashes main)

## Trainers gate

- Known trainer → amount lands in its row
- Unknown trainer → **held out** of numbers → proposal in דגלים + pending_trainers_*.json
- No silent placement of anything uncertain
