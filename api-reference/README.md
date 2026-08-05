# Regenerating the API specs

Not in the Mintlify nav. This is a note for whoever has to update these files.

There are three, and only two of them are generated. Knowing which is which is
the whole point of this note: the last update went eight weeks stale because
that distinction was not written down anywhere.

## `openapi.json` and `openapi.yaml` are generated

Machine output from the running FastAPI app, covering the whole REST surface.
Regenerate both from the platform repo:

```bash
cd blindsight-platform-runtime-security/backend
export DATABASE_URL=... DATA_DIR=... CONTENT_ENCRYPTION_KEY=... \
       AUTH_COOKIE_SECURE=false KEYGEN_DEV_MODE=true PUBLIC_APP_URL=...
python3 -c 'import json; from app.main import app; json.dump(app.openapi(), open("/tmp/openapi.json","w"), indent=2)'
```

Then, in this repo, three post-processing steps that must not be skipped:

1. **Set `servers` and `info`.** FastAPI emits neither usefully. The prose in
   these docs uses `https://api.your-blindsight.com` as the placeholder host,
   because the product is self-hosted. Keep the spec agreeing with the prose.
2. **Drop `injection_model` from `RuntimeSecurityConfig-Input`.** Its Pydantic
   default IS the detector's identifier, so FastAPI bakes the model id into the
   published schema. The field is excluded from responses anyway. Detector
   identities are backend-only and must never reach a published artifact.
3. **Replace em dashes.** House rule, and the backend docstrings they come from
   still contain them.

Check all three before committing:

```bash
grep -icE 'gliner|deberta|protectai|deepset|fastino|testsavantai' api-reference/*
grep -c '—' api-reference/openapi.yaml
python3 -c "import json,yaml;json.load(open('api-reference/openapi.json'));yaml.safe_load(open('api-reference/openapi.yaml'))"
```

Matches on `huggingface` are fine when they are the dataset-import integration,
which is a real product feature. They are not fine when they describe a
detector.

## `openapi-runtime-security.yaml` is hand written

Do **not** regenerate it. It is a curated 14-path integration spec covering
what an integrator actually calls: scan, proxy, tool calls, config, events,
health. It carries worked examples and prose that generation would destroy.

The app currently exposes about 127 runtime-security paths. The other ~113 are
admin and endpoint-agent routes that would drown the integration surface, so
their absence is deliberate, not staleness.

What DOES need checking against the app, because it drifts silently:

- every path in it still exists
- `RuntimeSecurityConfig` matches `RuntimeSecurityConfig-Input`, minus
  `injection_model`
- `NerStatus` has no `model` field. `get_status()` in `ner_pii.py` explicitly
  pops `model` and `model_path`, and the spec once documented a field the API
  never returned.

## Sanity check

`openapi.json` currently has 411 paths. If a regeneration produces far fewer,
the app probably failed to import a router rather than the routes having gone.
