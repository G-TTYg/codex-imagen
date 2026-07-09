# Codex Imagen

Codex Imagen is a local Codex plugin for generating images with GPT image models from the same API configuration Codex already uses.

The plugin includes:

- a Codex skill at `plugins/codex-imagen/skills/generate-codex-image`
- a reusable generation script at `plugins/codex-imagen/scripts/generate_image.py`
- a plugin manifest at `plugins/codex-imagen/.codex-plugin/plugin.json`
- a repo-local marketplace entry at `.agents/plugins/marketplace.json`

By default, the script uses `gpt-image-2`.

## What It Does

Codex Imagen standardizes image generation for Codex workflows. Instead of asking every image-generation task to configure a separate API key or write a new helper script, this plugin reuses the user's existing Codex setup.

The script automatically reads:

- `CODEX_HOME/config.toml`, or `~/.codex/config.toml`
- `CODEX_HOME/auth.json`, or `~/.codex/auth.json`
- environment variables such as `OPENAI_API_KEY`, `CODEX_OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `CODEX_OPENAI_BASE_URL`

It then calls an OpenAI-compatible image generation endpoint:

```text
<base_url>/images/generations
```

When one or more reference/source images are provided with `--image`, it automatically calls:

```text
<base_url>/images/edits
```

This works well when Codex is configured in API-key mode with an OpenAI-compatible provider.

## Repository Layout

```text
.
├── .agents/
│   └── plugins/
│       └── marketplace.json
└── plugins/
    └── codex-imagen/
        ├── .codex-plugin/
        │   └── plugin.json
        ├── scripts/
        │   └── generate_image.py
        └── skills/
            └── generate-codex-image/
                └── SKILL.md
```

## Installation

### Option 1: Use This Repository As A Local Marketplace

Clone the repository:

```powershell
git clone https://github.com/G-TTYg/codex-imagen.git
cd codex-imagen
```

The repository already contains `.agents/plugins/marketplace.json`, which points to `./plugins/codex-imagen`.

In Codex, add or enable this local marketplace/repository as a plugin source, then install or enable `codex-imagen`.

### Option 2: Copy The Plugin Into Your Codex Home

Clone the repository:

```powershell
git clone https://github.com/G-TTYg/codex-imagen.git
```

Copy the plugin folder into your Codex plugin area:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\plugins\local" | Out-Null
Copy-Item -Recurse -Force ".\codex-imagen\plugins\codex-imagen" "$env:USERPROFILE\.codex\plugins\local\codex-imagen"
```

Then enable the plugin from Codex if your Codex build exposes local plugin management.

## Requirements

- Python 3.11 or newer is recommended.
- Codex must already have API-key auth configured.
- The configured provider must support an OpenAI-compatible Images API.

For Python 3.10 or older, install `tomli`:

```powershell
python -m pip install tomli
```

## Usage

Run the script from the repository root:

```powershell
python plugins\codex-imagen\scripts\generate_image.py --prompt "A compact blue app icon, transparent background" --output icon.png --background transparent
```

Or from the plugin root:

```powershell
cd plugins\codex-imagen
python .\scripts\generate_image.py --prompt "A clean product mockup on white background" --output mockup.png
```

Use a reference image:

```powershell
python plugins\codex-imagen\scripts\generate_image.py --prompt "Restyle this product photo as a clean studio render" --image product.png --output studio-render.png
```

Use multiple reference images:

```powershell
python plugins\codex-imagen\scripts\generate_image.py --prompt "Combine the character style from ref1 with the color palette from ref2" --image ref1.png --image ref2.png --output combined.png
```

Use a mask for localized edits:

```powershell
python plugins\codex-imagen\scripts\generate_image.py --prompt "Replace the background with a minimal white studio" --image photo.png --mask mask.png --output edited.png
```

Useful options:

- `--model gpt-image-2`
- `--image path\to\reference.png`
- `--mask path\to\mask.png`
- `--size 1024x1024`
- `--quality auto`
- `--background transparent`
- `--n 1`
- `--dry-run`

Verify configuration without sending a generation request:

```powershell
python plugins\codex-imagen\scripts\generate_image.py --prompt "test" --dry-run
```

The dry-run output redacts secrets and only reports whether an API key was found.

## Codex Skill Usage

Once the plugin is installed, ask Codex for image-generation work naturally, for example:

```text
Generate a transparent PNG icon of a glass camera.
```

The `generate-codex-image` skill instructs Codex to call the bundled script, reuse the current Codex API configuration, save the output in the workspace, and show or reference the generated file.

## Notes

- This plugin does not store API keys.
- The script never prints the key in diagnostics.
- If your configured provider does not support `/images/generations`, the script will show the provider/base URL and the HTTP error so an adapter can be added.
