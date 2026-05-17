# Seed Schema Design

Seed data is loaded automatically in a later phase, but the schema is fixed in Phase 2 so backend, agents, tests, and UI can develop against the same contract.

## Manifest

`seed_manifest.yaml`

Required fields:

- `version`
- `tenant_slug`
- `files`
- `provenance`

All seeded records must set `source_type: seeded`. Live integration records must use `source_type: imported`; LLM-generated records must use `source_type: generated`.

## Files

| File | Purpose | Key fields |
| --- | --- | --- |
| `tenants.yaml` | Demo tenant | `slug`, `name` |
| `users.yaml` | Review users | `tenant_slug`, `email`, `full_name`, `roles`, `permissions` |
| `personas.yaml` | Buyer personas | `key`, `name`, `description`, `buying_committee_role` |
| `icps.yaml` | Ideal customer profiles | `key`, `name`, `description`, `criteria`, `target_personas` |
| `accounts.yaml` | Prospect accounts | `key`, `name`, `domain`, `lifecycle_stage`, `firmographics`, `custom_fields` |
| `contacts.yaml` | Contacts attached to accounts | `key`, `account_key`, `persona_key`, `email`, `full_name`, `title` |
| `signals.yaml` | Intent signals attached to accounts | `key`, `account_key`, `source`, `signal_type`, `strength`, `payload`, `observed_at` |
| `custom_fields.yaml` | Tenant field definitions | `entity_type`, `field_name`, `field_type`, `validation_rules`, `default_value`, `metadata` |
| `value_hypotheses.yaml` | Optional generated value hypotheses | `key`, `account_key`, `contact_key`, `workflow_key`, `generated`, `generated_by_agent`, `generated_at`, `confidence_score`, `title`, `hypothesis`, `metadata` |
| `outreach_drafts.yaml` | Optional generated outreach drafts | `key`, `account_key`, `contact_key`, `workflow_key`, `generated`, `generated_by_agent`, `generated_at`, `confidence_score`, `subject`, `body`, `status`, `metadata` |
| `workflow_outputs.yaml` | Optional generated workflow fixtures | `workflow_key`, `generated`, `workflow_type`, `status`, `input`, `output` |

## Reference Rules

- Seed keys are local file references only and are resolved to UUIDs by the seed loader.
- Cross-file references must remain tenant-local.
- `contacts.account_key`, `signals.account_key`, generated artifact references, and persona/ICP references must fail fast when unresolved.
- Seed loader writes must be idempotent per tenant and key.
- Generated fixtures must set `generated: true` and `source_type: generated` where a table supports provenance fields.

## Minimum Demo Counts

- 1 tenant
- 2 ICPs
- 3 personas
- 10 accounts
- 10 contacts
- 10 signals

Optional generated fixtures:

- Value hypotheses
- Outreach drafts
- Workflow outputs

## Review Provenance

The UI and README must distinguish:

- Seeded data: bundled demo records from `/data`
- Imported data: records from a live provider integration
- Generated data: value hypotheses, outreach drafts, and agent-created artifacts

## Scoring and Cost Notes

- `signals.strength` is a 0-100 intent score, where higher values indicate stronger buying intent.
- Generated artifact `confidence_score` is a 0-100 model confidence indicator.
- `llm_usage_records` track `model`, `token_input`, `token_output`, `estimated_cost`, and `latency_ms` so the Prospect workflow can report cost and latency evidence.
