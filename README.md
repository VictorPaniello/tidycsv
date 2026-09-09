# tidycsv

A config-driven CLI that turns a messy client CSV/Excel export into a clean,
validated dataset — plus a report of exactly what it fixed and what it
couldn't.

## Why this exists

Client data never arrives clean: headers vary between exports ("Email
Address" vs "E-mail" vs "Correo"), dates show up in three different formats,
currency fields carry symbols and thousands separators, and the same person
turns up twice with slightly different casing. Every integration project
starts with this same unglamorous cleanup step before the real work can
begin.

`tidycsv` handles that step generically: you describe your target schema
once (as a small YAML file, mapping every header spelling you expect onto a
canonical field name), and it does the column mapping, type coercion, and
validation for you — instead of writing one-off pandas scripts per client
export.

I built this while preparing for Forward Deployed Engineer roles, using
[Claude Code](https://claude.com/claude-code) as a pair-programmer, to have
something concrete to point to for the "client data arrives messy, you make
it usable" part of the job rather than just talking about it.

## Install

```bash
git clone https://github.com/VictorPaniello/tidycsv.git
cd tidycsv
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Usage

```bash
tidycsv examples/messy_client_export.csv \
  --schema examples/schema.example.yaml \
  --output clean.csv \
  --report report.json
```

```
          tidycsv -
   messy_client_export.csv
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric             ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Rows in            │     6 │
│ Rows clean         │     2 │
│ Rows flagged       │     3 │
│ Duplicates dropped │     1 │
└────────────────────┴───────┘
   Issues by column
┏━━━━━━━━━━━━━┳━━━━━━━┓
┃ Column      ┃ Count ┃
┡━━━━━━━━━━━━━╇━━━━━━━┩
│ full_name   │     1 │
│ email       │     1 │
│ signup_date │     1 │
│ phone       │     1 │
└─────────────┴───────┘

Clean file: clean.csv
Report: report.json
```

(Run it yourself — this is real output from `examples/messy_client_export.csv`, not a mockup.)

### Writing a schema

```yaml
fields:
  - name: full_name
    aliases: ["name", "Full Name", "Nombre"]
    type: string
    required: true

  - name: email
    aliases: ["e-mail", "Email Address", "correo"]
    type: email
    required: true

  - name: signup_date
    aliases: ["Signup Date", "fecha_alta"]
    type: date

  - name: amount
    aliases: ["Amount", "Total ($)"]
    type: currency

key_columns: ["email"]   # rows sharing this value (after cleaning) are deduplicated
```

Supported field types: `string`, `email`, `date` (normalized to ISO 8601),
`currency` (strips symbols/separators), `integer`, `phone`.

Any input column not mentioned in the schema is dropped rather than passed
through silently — the schema is the contract for what "clean" means, not a
best-effort pass.

## What it doesn't do (yet)

- Fuzzy/near-duplicate matching — only exact matches on the key columns
  after cleaning are deduplicated.
- Custom validation rules beyond the built-in field types.
- Streaming for very large files (loads the whole file into memory via
  pandas).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT
