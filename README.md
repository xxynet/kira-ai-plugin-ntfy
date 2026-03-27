# kira-ai-plugin-ntfy

A [KiraAI](https://github.com/xxynet/KiraAI) plugin that sends push notifications via [ntfy](https://ntfy.sh).

## Features

- Push notifications to any ntfy topic
- Optionally register as an LLM tool, letting the AI send notifications on its own

## Installation

Place this folder under `data/plugins/` in your KiraAI installation, then enable it in the plugin settings.

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `topic_url` | string | `""` | Full ntfy topic URL to push to (e.g. `https://ntfy.sh/your-topic`) |
| `as_tool` | switch | `false` | Register ntfy as an LLM tool so the AI can send notifications autonomously |

## Usage

### As an LLM Tool

Enable **As Tool** in the plugin settings. When active, the AI can call the `ntfy` tool with the following parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `msg` | yes | Notification body |
| `title` | no | Notification title |

### From Another Plugin

`NtfyPlugin` exposes a `push_notification` method that other plugins can call directly:

```python
ntfy: NtfyPlugin = ctx.get_plugin("kira-ai-plugin-ntfy")
await ntfy.push_notification(msg="Hello!", title="My Title")
```

## Requirements

- Python 3.10+
- [`httpx`](https://www.python-httpx.org/)
- A running ntfy server or access to [ntfy.sh](https://ntfy.sh)
