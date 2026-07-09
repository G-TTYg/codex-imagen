#!/usr/bin/env python3
"""Generate images using Codex's existing API configuration."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import mimetypes
import os
import pathlib
import sys
import urllib.error
import urllib.request
import uuid

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


DEFAULT_MODEL = "gpt-image-2"


def codex_home() -> pathlib.Path:
    return pathlib.Path(os.environ.get("CODEX_HOME") or pathlib.Path.home() / ".codex")


def load_toml(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_json(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_config() -> dict:
    home = codex_home()
    config = load_toml(home / "config.toml")
    auth = load_json(home / "auth.json")
    provider_name = os.environ.get("CODEX_MODEL_PROVIDER") or config.get("model_provider") or "openai"
    providers = config.get("model_providers") or {}
    provider = providers.get(provider_name, {})
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("CODEX_OPENAI_API_KEY")
        or auth.get("OPENAI_API_KEY")
        or auth.get("api_key")
        or provider.get("api_key")
    )
    base_url = (
        os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("CODEX_OPENAI_BASE_URL")
        or provider.get("base_url")
        or "https://api.openai.com/v1"
    )
    return {
        "codex_home": str(home),
        "config_path": str(home / "config.toml"),
        "auth_path": str(home / "auth.json"),
        "preferred_auth_method": config.get("preferred_auth_method"),
        "provider_name": provider_name,
        "provider": provider,
        "api_key": api_key,
        "base_url": str(base_url).rstrip("/"),
    }


def default_output(index: int = 0) -> pathlib.Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{index + 1}" if index else ""
    return pathlib.Path.cwd() / f"codex-imagen-{stamp}{suffix}.png"


def build_payload(args: argparse.Namespace) -> dict:
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "n": args.n,
        "size": args.size,
    }
    optional_fields = {
        "quality": args.quality,
        "background": args.background,
        "style": args.style,
        "moderation": args.moderation,
        "output_format": args.output_format,
        "output_compression": args.output_compression,
        "user": args.user,
    }
    for key, value in optional_fields.items():
        if value is not None:
            payload[key] = value
    return payload


def request_json(base_url: str, api_key: str, payload: dict) -> dict:
    endpoint = f"{base_url}/images/generations"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Image API returned HTTP {exc.code}: {detail}") from exc


def guess_mime_type(path: pathlib.Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def multipart_field(boundary: str, name: str, value: object) -> bytes:
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{value}\r\n"
    ).encode("utf-8")


def multipart_file(boundary: str, name: str, path: pathlib.Path) -> bytes:
    filename = path.name
    mime_type = guess_mime_type(path)
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8")
    return header + path.read_bytes() + b"\r\n"


def build_multipart_body(args: argparse.Namespace, payload: dict) -> tuple[bytes, str]:
    boundary = f"codex-imagen-{uuid.uuid4().hex}"
    chunks = []
    for key, value in payload.items():
        if value is not None:
            chunks.append(multipart_field(boundary, key, value))
    for image_path in args.image:
        chunks.append(multipart_file(boundary, "image", image_path))
    if args.mask:
        chunks.append(multipart_file(boundary, "mask", args.mask))
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def request_edit(base_url: str, api_key: str, args: argparse.Namespace, payload: dict) -> dict:
    endpoint = f"{base_url}/images/edits"
    body, boundary = build_multipart_body(args, payload)
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Image edit API returned HTTP {exc.code}: {detail}") from exc


def validate_input_images(args: argparse.Namespace) -> None:
    if len(args.image) > 16:
        raise SystemExit("GPT image models support up to 16 input images.")
    for path in [*args.image, *([args.mask] if args.mask else [])]:
        if not path.exists():
            raise SystemExit(f"Input image does not exist: {path}")
        if not path.is_file():
            raise SystemExit(f"Input image is not a file: {path}")
    if args.mask and not args.image:
        raise SystemExit("--mask requires at least one --image.")


def write_images(response: dict, output: pathlib.Path | None) -> list[pathlib.Path]:
    items = response.get("data") or []
    if not items:
        raise RuntimeError(f"Image API response did not include data: {json.dumps(response)[:1000]}")
    written = []
    for index, item in enumerate(items):
        target = output or default_output(index)
        if len(items) > 1 and output:
            target = output.with_name(f"{output.stem}-{index + 1}{output.suffix or '.png'}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if item.get("b64_json"):
            target.write_bytes(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            with urllib.request.urlopen(item["url"], timeout=300) as response:
                target.write_bytes(response.read())
        else:
            raise RuntimeError(f"Image item has neither b64_json nor url: {json.dumps(item)[:1000]}")
        written.append(target.resolve())
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate images using Codex's existing API configuration.")
    parser.add_argument("--prompt", required=True, help="Image prompt to send to the model.")
    parser.add_argument("--output", type=pathlib.Path, help="Output PNG path. Multiple images add -1, -2, etc.")
    parser.add_argument("--image", action="append", type=pathlib.Path, default=[], help="Reference/source image path. Repeat up to 16 times. When set, the script uses /images/edits.")
    parser.add_argument("--mask", type=pathlib.Path, help="Optional PNG mask for editing the first input image.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Image model. Default: {DEFAULT_MODEL}.")
    parser.add_argument("--size", default="1024x1024", help="Image size, for example 1024x1024 or auto.")
    parser.add_argument("--quality", default="auto", help="Quality: auto, low, medium, or high.")
    parser.add_argument("--background", default=None, help="Background: transparent, opaque, or auto.")
    parser.add_argument("--style", default=None, help="Optional style value for providers that support it.")
    parser.add_argument("--moderation", default=None, help="Optional moderation mode for providers that support it.")
    parser.add_argument("--output-format", default="png", choices=["png", "jpeg", "webp"], help="Output format.")
    parser.add_argument("--output-compression", type=int, default=None, help="Compression for jpeg/webp when supported.")
    parser.add_argument("--user", default=None, help="Optional end-user identifier.")
    parser.add_argument("--n", type=int, default=1, help="Number of images to generate.")
    parser.add_argument("--dry-run", action="store_true", help="Print resolved non-secret config and request payload.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_input_images(args)
    resolved = resolve_config()
    payload = build_payload(args)
    endpoint = "edits" if args.image else "generations"
    diagnostic = {
        "codex_home": resolved["codex_home"],
        "config_path": resolved["config_path"],
        "auth_path": resolved["auth_path"],
        "preferred_auth_method": resolved["preferred_auth_method"],
        "provider_name": resolved["provider_name"],
        "base_url": resolved["base_url"],
        "has_api_key": bool(resolved["api_key"]),
        "endpoint": f"/images/{endpoint}",
        "input_images": [str(path) for path in args.image],
        "mask": str(args.mask) if args.mask else None,
        "payload": payload,
    }
    if args.dry_run:
        print(json.dumps(diagnostic, indent=2, ensure_ascii=False))
        return 0
    if not resolved["api_key"]:
        print(json.dumps(diagnostic, indent=2, ensure_ascii=False), file=sys.stderr)
        raise SystemExit("No API key found in environment, Codex auth.json, or provider config.")
    if args.image:
        response = request_edit(resolved["base_url"], resolved["api_key"], args, payload)
    else:
        response = request_json(resolved["base_url"], resolved["api_key"], payload)
    for path in write_images(response, args.output):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
