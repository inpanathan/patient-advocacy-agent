---
name: sync-requirements
description: Sync requirement controller JSON files from markdown requirement documents
disable-model-invocation: true
argument-hint: "[--dry-run]"
---

Sync requirement controllers from their markdown source files.

```bash
bash scripts/sync_requirements.sh $ARGUMENTS
```

After syncing:
1. Report which requirements were added, removed, or updated
2. If `--dry-run` was used, show what would change without writing files
3. If actual sync was run, verify the JSON files are valid:
   ```bash
   uv run python -c "import json; [json.load(open(f)) for f in __import__('glob').glob('docs/requirements/*_controller.json')]"
   ```
