# CustomerQuery

NLP-to-SQL prompt construction, SQL validation, and an in-memory invoice dataset.

## Layout

```text
db/
  database.py              # SQLite schema and empty database factory
  sample_data.py           # Alice and Bob sample invoice factory
  engine.py                # SQLiteDBEngine connection lifecycle
  executor.py              # SQL execution and dictionary results
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

The engine manages connection creation and cleanup. `DatabaseExecutor` uses
its connection to execute SQL and return results. Closing the engine discards its in-memory database;
reconnecting starts a new empty one. The sample-data factory remains separate
and returns a populated connection that the caller must close.


## Execute queries

```python
from db.executor import DatabaseExecutor
from db.sample_data import create_sample_database

connection = create_sample_database()
try:
    executor = DatabaseExecutor(connection)
    results = executor.execute(
        "SELECT COUNT(*) AS unpaid_count FROM invoices WHERE invoice_status = 'unpaid'"
    )
    print(results)  # [{'unpaid_count': 6}]
finally:
    connection.close()
```

`execute(sql_query)` returns a list of dictionaries, or an empty list when no
rows are returned. Use unique column aliases for joins with duplicate column
names. Database errors propagate; the caller controls transactions and connection
cleanup. Validate LLM-generated SQL with `SQLQueryValidator` before execution.
