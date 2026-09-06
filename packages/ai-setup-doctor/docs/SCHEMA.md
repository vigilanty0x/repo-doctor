# Schema 1.0

A report contains exactly `schema_version`, `report_id`, `diagnostics`, and `summary`.

Each diagnostic contains:

- `tool`: unique human-readable name;
- `status`: `installed`, `missing`, `blocked`, or `error`;
- `evidence_class`: `proof`, `inference`, or `blockage`;
- `summary`: bounded explanation;
- `checked_command`: bounded argv description;
- `executable`, `version`, `exit_code`, and `error_code`: nullable evidence fields.

`report_id` is the lowercase SHA-256 of canonical JSON containing schema version, sorted diagnostics, and computed summary. Canonical JSON uses UTF-8, sorted object keys, no insignificant whitespace, and unescaped Unicode.

A journal event contains exactly `event_id`, `kind`, `report_id`, and `payload`. `kind` is `diagnostic_report`; `event_id` hashes the kind and report ID. Validators recompute report, summary, report ID, and event ID instead of trusting them.

