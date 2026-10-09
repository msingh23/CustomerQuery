# CustomerQuery

NLP-to-SQL prompt construction, SQL validation, and an in-memory invoice dataset.

## Layout

```text
db/
  database.py              # SQLite schema and empty database factory
  sample_data.py           # Alice and Bob sample invoice factory
  engine.py                # SQLiteDBEngine connection lifecycle scaffold
llm/
  llm_query_translator.py   # Prompt template and examples
validator/
  sql_query_validator.py   # Configurable SQL allowlist validation
tests/                     # Database, engine, sample-data, and validator tests
main.py                    # Hello World entry point
plan.md                    # Design and next steps
```

## Setup and checks

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m db.sample_data
.venv/bin/python main.py
```

SQLite is included with Python; SQLGlot is the external validation dependency.

## Interfaces

```python
from db.engine import SQLiteDBEngine
from db.sample_data import create_sample_database
from llm.llm_query_translator import LLMQueryTranslator, GoodExample, BadExample
from validator.sql_query_validator import SQLQueryValidator, SQLValidationRules

with SQLiteDBEngine() as engine:
    connection = engine.connect()  # Empty invoice/user schema; reused until close.
```

The engine currently manages connection creation and cleanup. Data-access
methods are the next step. Closing the engine discards its in-memory database;
reconnecting starts a new empty one. The sample-data factory remains separate
and returns a populated connection that the caller must close.
