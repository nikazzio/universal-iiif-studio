# Troubleshooting

This page covers the most common problems that users hit before they need deeper technical docs.

## `scriptoria: command not found`

Activate the virtual environment and reinstall in editable mode:

```bash
source .venv/bin/activate
pip install -e .
```

## Studio Opens Without A Document

This is expected. Opening `/studio` without `doc_id` and `library` shows the recent-work hub.

## Studio Shows Remote Images Instead Of Local Images

Check:

- `settings.viewer.mirador.require_complete_local_images`;
- the `allow_remote_preview=1` query override;
- current local page availability.

## Pages Stay In Staging

`settings.storage.partial_promotion_mode` controls when validated staged pages move into local `scans/`.

- `never` waits for completeness gates;
- `on_pause` promotes validated pages when the running job is paused.

## Providers Feel Slow

Per-library rate limiting and backoff can be stricter for fragile upstream services. Review:

- `settings.network.global.*`
- `settings.network.libraries.<library>.*`

## Read Next

- [Configuration Overview](../reference/configuration.md)
- [Runtime Paths](../reference/runtime-paths.md)
- [Security And Path Safety](../explanation/security-and-path-safety.md)
