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
  input/
    query.py                # Natural-language input screening
  output/
    sql_query_validator.py   # SQL allowlist validation
    user_query_validator.py  # Authenticated user scope validation
tests/                     # Database, engine, sample-data, and validator tests
cli.py                     # User ID/query argument parsing
models/invoice.py          # Invoice response data class
main.py                    # CLI entry point
plan.md                    # Design and next steps
```

## Setup and checks

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m db.sample_data
.venv/bin/python main.py --help
```

SQLite is included with Python; SQLGlot is the external validation dependency.

## Interfaces

```python
from db.engine import SQLiteDBEngine
from db.sample_data import create_sample_database
from llm.llm_query_translator import LLMQueryTranslator, GoodExample, BadExample
from validator.output import SQLQueryValidator, SQLValidationRules

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

## Validate authenticated user scope

```python
from validator.output import UserQueryValidator

validator = UserQueryValidator()
valid, reason = validator.validate(
    "SELECT * FROM invoices WHERE user_id = 1",
    original_user=1,  # Obtain from trusted authentication context.
)
```

Use both the application's configured `SQLQueryValidator` and this validator
before calling the executor. User validation returns `(True, None)` or
`(False, reason)`. It supports one SELECT over `invoices` and/or `users`,
requiring a mandatory WHERE equality to the authenticated integer user ID for
each table alias. It rejects unsupported constructs, other user-ID equality
values, ambiguous scope, and missing filters. CTEs, subqueries, and unions are
unsupported. For joins, explicitly scope both aliases:

```sql
SELECT i.invoice_id, u.name
FROM invoices i JOIN users u ON i.user_id = u.user_id
WHERE i.user_id = 1 AND u.user_id = 1
```

Scope conditions under OR or NOT do not establish mandatory scope. The
executor itself does not automatically run these validators; `QueryOrchestrator`
checks their boolean results before execution.


## CLI and invoice response object

```bash
python3 main.py --user-id 1 --query 'how many are unpaid'
```

Quote shell input with single quotes when it contains dollar amounts to avoid
shell expansion, for example:

```bash
python3 main.py --user-id 1 --query 'show invoices over $10,000'
```

`cli.parse_arguments()` returns a `QueryRequest` with a positive integer user ID
and validated natural-language query. Invalid input exits with code 2. The CLI
currently returns a JSON failure with `invoices: null` and exit code 1 because
model integration is pending; it does not execute a query or fabricate results.
A supplied CLI ID is a local development input, not authentication.

`models.invoice.Invoice` is a frozen data class with `invoice_id`,
`invoice_amount`, `invoice_date`, `invoice_status`, and `user_id`.
`Invoice.from_row(row)` maps a full invoice result dictionary; use
`dataclasses.asdict(invoice)` for JSON serialization. Aggregate results such as
counts need a separate response shape in the future.

`UserInputValidator` maintains SQL keywords and uses case-insensitive regex
matching to reject direct SQL or database constructs. It is intentionally a
simple heuristic and may reject ordinary phrases such as "update my invoices".
It cannot detect all injection attempts and does not replace generated-SQL
validation or user-scope validation.


## Happy-flow orchestration

`QueryOrchestrator.run(user_input, user_id)` validates input, builds the
translator prompt with schema, rules, examples, current date, and caller ID,
invokes `LLMClient.generate(prompt)`, validates the decoded JSON and SQL rules,
checks user scope, executes via the engine connection, and maps rows into a
`QueryResponse(invoices, reasoning)` through `InvoiceResponseMapper`.

```python
from application import create_orchestrator
from db.engine import SQLiteDBEngine
from db.sample_data import create_sample_database

# Supply your provider client implementing generate(prompt) -> JSON text.
with SQLiteDBEngine(database_factory=create_sample_database) as engine:
    orchestrator = create_orchestrator(engine, llm_client=your_llm_client)
    response = orchestrator.run("show unpaid invoices", user_id=1)
```

The CLI invokes this same flow after argument parsing and serializes the
response data classes to JSON. No real LLM provider has been configured; the
default client reports that prerequisite. Integration tests use a test client,
not a real model. The current happy flow returns full invoice records and does
not support aggregate responses. Application error-case design remains future
work; failed validation raises an exception. The caller owns engine cleanup.
