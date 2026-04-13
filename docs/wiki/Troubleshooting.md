# Troubleshooting

Use this page for the most common user-facing problems.

## `scriptoria: command not found`

```bash
source .venv/bin/activate
pip install -e .
```

## Studio Opens Without A Document

This is expected. `/studio` without document context opens the recent-work hub.

## Remote Images Are Shown Instead Of Local Images

This usually means the local dataset is incomplete or remote preview is active.

## Pages Stay In Staging

Check `settings.storage.partial_promotion_mode`.

## Read Next

- [Troubleshooting Guide](../guides/troubleshooting.md)
