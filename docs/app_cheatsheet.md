# App Cheatsheet

## Scripts

### Sync Requirements Controller

Regenerates `docs/common_requirements_controller.json` from `docs/common_requirements.md`. Preserves any `implement`/`enable` flags already set to `"Y"`.

```bash
# Preview changes (no files written)
./scripts/sync_requirements.sh --dry-run

# Apply changes
./scripts/sync_requirements.sh
```
