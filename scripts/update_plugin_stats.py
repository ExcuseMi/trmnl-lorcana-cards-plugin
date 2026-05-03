#!/usr/bin/env python3
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml


def load_plugin_id() -> int | None:
    settings_path = Path('plugin/src/settings.yml')
    if not settings_path.exists():
        return None
    with open(settings_path) as f:
        settings = yaml.safe_load(f)
    return settings.get('id')


def download_image(url: str, save_path: str) -> bool:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        content_type = resp.headers.get('Content-Type', '')
        if 'svg' in content_type:
            ext = '.svg'
        elif 'png' in content_type:
            ext = '.png'
        elif 'jpeg' in content_type or 'jpg' in content_type:
            ext = '.jpg'
        elif 'webp' in content_type:
            ext = '.webp'
        else:
            ext = Path(save_path).suffix or '.png'
        final_path = Path(save_path).with_suffix(ext)
        new_content = resp.content
        if final_path.exists():
            if hashlib.md5(final_path.read_bytes()).hexdigest() == hashlib.md5(new_content).hexdigest():
                return str(final_path)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_bytes(new_content)
        return str(final_path)
    except Exception as e:
        print(f'⚠️  Failed to download {url}: {e}')
        return None


def fetch_plugin_data(plugin_id: int) -> dict | None:
    try:
        resp = requests.get(f'https://trmnl.com/recipes/{plugin_id}.json', timeout=15)
        resp.raise_for_status()
        return resp.json().get('data')
    except Exception as e:
        print(f'⚠️  Failed to fetch plugin {plugin_id}: {e}')
        return None


def generate_stats_section(plugin_id: int, images_dir: str) -> str:
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    data = fetch_plugin_data(plugin_id)

    if not data:
        return (
            f'## 🔒 Plugin ID: {plugin_id}\n\n'
            f'**Status**: ⏳ Not yet published on TRMNL or API unavailable\n\n'
            f'This plugin is configured but either hasn\'t been published to the TRMNL marketplace yet '
            f'or the API is temporarily unavailable.\n\n'
            f'**Plugin URL**: https://usetrmnl.com/recipes/{plugin_id}\n\n---\n'
        )

    name = data.get('name', f'Plugin {plugin_id}')
    icon_url = data.get('icon_url', '')
    screenshot_url = data.get('screenshot_url', '')
    description = (data.get('author_bio') or {}).get('description', '')

    icon_path = screenshot_path = None
    if icon_url:
        icon_path = download_image(icon_url, f'{images_dir}/{plugin_id}_icon.png')
    if screenshot_url:
        screenshot_path = download_image(screenshot_url, f'{images_dir}/{plugin_id}_screenshot.png')

    lines = []
    if icon_path:
        lines.append(f'## <img src="{icon_path}" alt="{name} icon" width="32"/> [{name}](https://trmnl.com/recipes/{plugin_id})')
    else:
        lines.append(f'## [{name}](https://trmnl.com/recipes/{plugin_id})')
    lines.append('')
    lines.append(f'![Installs](https://trmnl-badges.gohk.xyz/badge/installs?recipe={plugin_id}) '
                 f'![Forks](https://trmnl-badges.gohk.xyz/badge/forks?recipe={plugin_id})')
    lines.append('')
    if screenshot_path:
        lines.append(f'![{name} screenshot]({screenshot_path})')
        lines.append('')
    if description:
        lines.append('### Description')
        lines.append(description)
        lines.append('')
    lines.append('---')
    return '\n'.join(lines) + '\n'


def update_readme(plugin_id: int, images_dir: str = 'assets/plugin-images'):
    readme_path = Path('README.md')
    if not readme_path.exists():
        print('⚠️  README.md not found')
        return

    content = readme_path.read_text()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    stats = generate_stats_section(plugin_id, images_dir)

    new_section = (
        f'<!-- PLUGIN_STATS_START -->\n'
        f'## 🚀 TRMNL Plugin(s)\n\n'
        f'*Last updated: {now}*\n\n\n'
        f'{stats}\n'
        f'<!-- PLUGIN_STATS_END -->'
    )

    pattern = r'<!-- PLUGIN_STATS_START -->.*?<!-- PLUGIN_STATS_END -->'
    new_content = re.sub(pattern, new_section, content, flags=re.DOTALL)
    if new_content == content:
        new_content = content + '\n' + new_section + '\n'

    readme_path.write_text(new_content)
    print(f'✅ README updated for plugin {plugin_id}')


if __name__ == '__main__':
    plugin_id = load_plugin_id()
    if not plugin_id:
        print('⚠️  No plugin ID found in plugin/src/settings.yml')
        exit(0)
    update_readme(plugin_id)
