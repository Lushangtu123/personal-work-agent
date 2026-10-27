# Batch import

The CLI and HTTP function are supported entry points. Imports accept at most
25 nonempty lines. Each line is `name,positive_integer`; returned names are
trimmed. Empty input returns an empty list. Errors are ValueError with the
messages already used by the entry points. There is no network or persistence.

`legacy_api.parse_record` is an existing integration surface. Its keyword name
`record` and tuple return are kept for downstream callers; they cannot migrate
in the upcoming release. `engine.parse_row` serves newer callers with a dict.
There is no benchmark, production telemetry or change history in this export.
