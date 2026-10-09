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

Provide the prompt template and Python class that assembles it. Keep the existing Hello World entry point. Model calls, database connections, SQL execution, and a user interface are future work.

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
