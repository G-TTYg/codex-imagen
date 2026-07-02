---
name: generate-codex-image
description: Generate raster images from Codex with GPT image models using the existing Codex API configuration. Use when the user asks Codex to create, generate, render, or save an image, PNG, illustration, visual asset, sprite, icon, mockup, or image variant through the user's configured Codex API key and provider instead of requiring separate plugin credentials.
---

# Generate Codex Image

Use the bundled script whenever an image should be generated through the user's Codex API settings.

## Workflow

1. Think through the image before spending generation time or API credits. Identify the subject, composition, style, size/aspect ratio, background, text, output format, and any constraints that must be right on the first attempt.
2. If an important requirement is missing and a reasonable default would risk wasting a generation, ask one concise clarification before generating.
3. Translate the user's request into one complete, high-quality image prompt. Preserve requested subject, style, aspect ratio, text, transparency, and output path.
4. Use `--dry-run` when checking configuration, model, output path, or provider behavior; dry-run does not send a generation request.
5. Run `scripts/generate_image.py` from the plugin root. The script automatically reads:
   - `CODEX_HOME/config.toml`, falling back to `~/.codex/config.toml`
   - `CODEX_HOME/auth.json`, falling back to `~/.codex/auth.json`
   - environment variables such as `OPENAI_API_KEY`
6. Save the output image in the user's workspace unless they asked for another location.
7. Show or reference the generated file with an absolute path.

## Commands

From the plugin root:

```powershell
python .\scripts\generate_image.py --prompt "A compact UI icon of a glass camera, transparent background" --output .\camera.png --background transparent
```

Useful options:

- `--model gpt-image-2` to choose the image model.
- `--size 1024x1024`, `1024x1536`, `1536x1024`, or `auto`.
- `--quality auto`, `low`, `medium`, or `high`.
- `--background transparent`, `opaque`, or `auto`.
- `--n 1` for the number of images.
- `--dry-run` to verify which Codex config and provider would be used without sending a request.

## Rules

- Avoid wasting generation time and API credits. Do not repeatedly generate vague, low-effort, or speculative variants when the user's intent can be resolved by thinking, improving the prompt, or asking a short clarification first.
- Default to one carefully planned generation. Generate additional images only when the user explicitly asks for variants, the first result failed technically, or there is a clear user-facing reason.
- Do not ask the user for an API key unless the script reports that Codex has no usable API key.
- Do not print secrets. The script redacts credentials in diagnostic output.
- Prefer PNG outputs for generated assets.
- If a provider does not support the OpenAI Images API, report the provider/base URL and the script error, then ask whether to add a provider-specific adapter.
