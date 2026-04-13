# Troubleshooting

Use this page for the most common user-facing problems. If a topic needs deeper explanation, jump to the full troubleshooting guide linked below.

## `scriptoria: command not found`

```bash
source .venv/bin/activate
pip install -e .
```

If the command is still missing after reinstalling, reopen the shell or verify that the virtual environment is actually active.

## Studio Opens Without A Document

This is expected. `/studio` without document context opens the recent-work hub.

## Remote Images Are Shown Instead Of Local Images

This usually means the local dataset is incomplete or remote preview is active. The most common cause is that the manuscript is still only partially local.

## Pages Stay In Staging

Check `settings.storage.partial_promotion_mode`.

## Read Next

- [Troubleshooting Guide](../guides/troubleshooting.md)
