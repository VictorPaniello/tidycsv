![tidycsv](.github/banner.svg)

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

- `input_file` (positional) and **`--schema` / `-s` are required** — there's
  no sensible default schema, since every client's columns are different.
  Omitting `--schema` fails immediately with `Missing option '--schema'`
  rather than guessing at your data.
- `--output` / `-o` and `--report` / `-r` are **optional** — they default to
  `clean.csv` and `report.json` in the current directory. So the minimal
  command is just:

  ```bash
  tidycsv examples/messy_client_export.csv --schema examples/schema.example.yaml
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
`currency`, `integer`, `phone`.

`currency` handles both US/UK-style (`"1,200.50"`) and EU-style
(`"1.200,50"` / `"99,99"`) separators — it infers which character is the
decimal point rather than blindly stripping commas. When only a comma is
present, exactly 2 trailing digits is treated as a decimal point (`"99,99"`
→ `99.99`), anything else as a thousands separator (`"12,345"` → `12345.00`).
This is a heuristic, not a locale setting, so a genuinely ambiguous input
(a comma-decimal amount that happens to have 3 trailing digits, e.g. a
non-EUR currency with 3 decimal places) can still be misread — there's no
way to know the source locale from the string alone.

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

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT
