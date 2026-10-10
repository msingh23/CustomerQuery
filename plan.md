# NLP-to-SQL query translator

## Goal

Translate a natural-language request into SQL for an invoice database. The SQL dialect is supplied as an input rather than hard-coded.

## Database context

The invoice table contains invoice ID, invoice amount, invoice date, invoice status, and user ID. A separate user table contains user information and is linked by user ID.

Exact table names, column names, types, user fields, and relationships must be supplied through table context. Names used in examples are illustrative until the actual schema is provided.

## Prompt structure

1. **Role:** act as a SQL expert in the supplied SQL dialect.
2. **SQL dialect:** inject the target SQL language, such as PostgreSQL, SQLite, or MySQL.
3. **Context:** inject table definitions, columns, relationships, and relevant business meanings.
4. **Rules:** inject application-specific rules and constraints.
5. **Examples:** inject good examples with expected SQL and bad examples with explanations of what to avoid.
6. **Request:** inject the natural-language question to translate.
7. **Output:** return a JSON object with `sql_query`, `reasoning`, and `failure`, without Markdown or text outside JSON.

## LLM response contract

The translator returns a prompt instructing the LLM to produce these separate fields:

- `sql_query`: SQL in the supplied dialect on success; `null` on failure.
- `reasoning`: a concise one- or two-sentence rationale describing the mapping from the request to tables, joins, filters, or aggregations; `null` on failure.
- `failure`: `null` on success; a concise reason when translation fails. Rule violations must identify the violated rule.

Successful response:

```json
{"sql_query": "SELECT invoice_id FROM invoices;", "reasoning": "Selects the invoice identifier from the invoice table.", "failure": null}
```

Failure response:

```json
{"sql_query": null, "reasoning": null, "failure": "The request violates the rule permitting only SELECT queries."}
```

Do not generate SQL for rule violations, ambiguous requests, insufficient schema information, or other translation failures. A response must never contain both a query and a failure reason. The rationale is a brief explanation of the SQL mapping.

## Python interface

`LLMQueryTranslator(sql_dialect, table_context, rules, good_examples, bad_examples)` holds the prompt inputs. `build_prompt(request)` returns the assembled prompt.

`GoodExample` contains a natural-language request and expected SQL. `BadExample` contains a request, incorrect SQL, and an explanation of why it is incorrect. Empty example collections leave explicit placeholders in the prompt.

## Current scope

Provide the prompt template and Python class that assembles it. Provide a CLI entry point for user ID and natural-language query input. Model calls, database connections, SQL execution, and a user interface are future work.

## Next steps

- Confirm the SQL dialect and actual database schema.
- Supply business rules, including invoice status meanings and any access restrictions.
- Add representative good and bad examples for filters, totals, dates, and invoice/user joins.
- Choose an LLM provider and integrate the generated prompt.
- Validate generated SQL against the selected dialect and schema before execution.
- Evaluate query results against a sample invoice database, including ambiguous requests.

## Open decisions

- Which SQL dialect and exact schema should be used?
- Should a future interface offer clarification when the LLM returns a failure for an ambiguous request?
- Which operations and user data may queries access?

## Scaffold validation

Verify that the prompt includes every supplied input, distinguishes good examples from bad examples, and defines the JSON success and failure contracts. Model response validation will be required when LLM calls are added. No model-generated SQL or database behavior is claimed at this stage.

## SQL validator

`SQLQueryValidator` is bootstrapped with `SQLValidationRules`. Its
`validate(sql_query, failure_codes=())` method returns `(True, None)` on
success or `(False, reason)` on failure. `validate_response(output,
failure_codes=())` accepts the translator's decoded JSON object and rejects
its non-null `failure` field. External failure codes are supplied separately;
the translator's three-field response contract remains unchanged.

Rules specify the SQLGlot dialect, exact allowed table identities, allowed
operations, join types, aggregation functions, and an explicit allowlist of
SQLGlot expression constructs. Initially only SELECT is supported; aggregations
are SELECT expressions such as SUM and COUNT. Tables must match their qualified
identity (for example, `public.invoices` must be listed separately). Table
aliases are supported. Join rules permit types such as INNER and LEFT, rather
than specific table pairs or relationships. Non-CROSS joins require ON or USING.

The validator parses SQL and rejects constructs outside the allowlist, multiple
statements, unsupported functions, CTEs, subqueries, and upstream LLM failures.
It does not execute SQL or verify column existence, database permissions, query
results, or join-key correctness. Syntax parsing is not database validation.

Example configuration:

```python
from validator.sql_query_validator import SQLQueryValidator, SQLValidationRules

validator = SQLQueryValidator(SQLValidationRules(
    dialect="postgres",
    allowed_tables=frozenset({"invoices", "users"}),
    allowed_operations=frozenset({"SELECT"}),
    allowed_joins=frozenset({"INNER", "LEFT"}),
    allowed_aggregations=frozenset({"SUM", "COUNT"}),
))
valid, reason = validator.validate("SELECT invoice_id FROM invoices")
```

Install and verify from the repository directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest -v
```

## In-memory invoice schema

`db.database.create_database()` returns a new SQLite connection with empty tables:

- `users`: `user_id INTEGER PRIMARY KEY` and nullable `name TEXT`.
- `invoices`: `invoice_id INTEGER PRIMARY KEY`, `invoice_amount NUMERIC NOT NULL`, `invoice_date TEXT NOT NULL`, `invoice_status TEXT NOT NULL`, and `user_id INTEGER NOT NULL` referencing `users.user_id`.

Foreign keys are enabled. Supply dates as `YYYY-MM-DD`; invoice status is restricted to `paid` or `unpaid` using a SQLite `CHECK` constraint (SQLite has no native enum type). SQLite NUMERIC affinity does not guarantee exact decimal monetary storage; choose an exact monetary representation before production use. No sample data is loaded.

```python
from db.database import create_database

connection = create_database()
try:
    # Populate users first, then their invoices, using parameterized inserts.
    print(connection.execute("SELECT * FROM invoices").fetchall())
finally:
    connection.close()
```

Keep the connection open while loading examples and querying them. Each call creates a separate database, and closing its connection discards its contents. Use `sqlite` as the SQLGlot dialect when validating SQLite queries.


## Sample invoice data

`db.sample_data.create_sample_database()` creates a fresh in-memory database with
Alice (`user_id=1`) and Bob (`user_id=2`), each with five invoices. Alice's
amounts are $12,000, $15,000, $18,000, $22,000, and $11,000; Bob's are $500,
$1,200, $2,500, $8,000, and $9,500. Each user has two paid and three unpaid
invoices. Dates are today, one month ago (two invoices), two months ago, and
three months ago, using calendar-month shifts and Los Angeles's current date.
Pass `as_of=date(2026, 10, 9)` for reproducible dates.

```python
from db.sample_data import create_sample_database

connection = create_sample_database()
try:
    print(connection.execute("SELECT * FROM invoices").fetchall())
finally:
    connection.close()
```

Run `python3 -m db.sample_data` to print all ten records. The original
`create_database()` still creates empty tables. The populated database exists
only while its connection remains open.

For the October 9, 2026 reference date, five invoices exceed $10,000 and six
are unpaid (three per user). September invoice totals are $33,000 for Alice
and $3,700 for Bob. These are invoice totals, not confirmed spending or payment
totals: interpreting “I” requires a user ID, and interpreting “spent” requires
an agreed business meaning. No payment dates are stored.

## Repository organization and DB engine

- `db/`: schema, sample data, and `SQLiteDBEngine`.
- `llm/`: query translator and example classes.
- `validator/`: SQL validator and injected rules.
- `tests/`: automated checks for these components.

`db.engine.SQLiteDBEngine` currently provides `connect()`, `close()`, and
context-manager support. It reuses one connection until closed, with foreign
keys enabled and the empty schema initialized. Reconnecting creates a fresh
in-memory database. Next, define and implement parameterized SQLite data-access
methods and their transaction behavior. Query execution is provided separately by `db.executor.DatabaseExecutor`. Updated imports and run commands are documented in `README.md`.


## Database executor

`DatabaseExecutor(connection)` uses an existing SQLite connection, including
one from `SQLiteDBEngine.connect()` or `create_sample_database()`.
`execute(sql_query)` executes one SQL statement and returns a list of dictionaries
keyed by result column name. Empty results and statements without result columns
return `[]`. Duplicate result names require explicit SQL aliases. Errors propagate
to the caller, which also owns commit, rollback, and connection cleanup. Validation
remains a separate step before executing LLM-generated SQL.

## Authenticated user query validation

`validator.user_query_validator.UserQueryValidator(dialect="sqlite")` provides
`validate(sql_query, original_user)` returning `(valid, reason)`. The user ID
must come from authentication, not model output or the natural-language request.
For the current invoice/user schema, each table alias must have an explicit,
mandatory `WHERE alias.user_id = original_user` equality. With one table the
column may be unqualified. Joins require each alias to be scoped independently.
The initial implementation rejects CTEs, subqueries, unions, unknown tables,
ambiguous user references, and unsupported SQL constructs. It does not infer
user scope through joins. Run this and the configured construct/rule validator
before execution. A future application orchestration layer must enforce that
sequence; the current executor remains a standalone component.


## User input and response scaffold

`cli.parse_arguments(argv)` requires `--user-id` (positive integer) and `--query`.
`UserInputValidator` screens the query using a maintained SQL keyword list and
regex patterns for database constructs. There is one input validator, with no
separate intent classifier. This heuristic may reject ordinary SQL-related
words and does not replace output validation.

`models.invoice.Invoice` defines the five invoice columns as a Python data
class and maps complete result rows through `from_row`. Aggregate queries will
need a separate result type. `main.py` validates input and explicitly reports
that LLM integration is not configured, returning no invoice data yet. Next,
connect the model, validate its output against application rules and trusted
user scope, execute the query, and map full invoice rows into response objects.
The CLI user ID is for local development; production must use authenticated
identity rather than trust a caller-supplied ID.
