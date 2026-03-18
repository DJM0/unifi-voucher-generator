#!/usr/bin/env python3
"""
UniFi Voucher Generator

Generates printable WiFi vouchers from a UniFi controller.
Supports both legacy UniFi Controller (5.x–8.x) and modern UniFi OS
devices (Dream Machine, UDM Pro, Cloud Key Gen 2+).

Usage:
    python3 generate.py --help
"""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
from html import escape


# ---------------------------------------------------------------------------
# UniFi API client
# ---------------------------------------------------------------------------

class UnifiClient:
    """Manages HTTP communication with a UniFi controller.

    Supports both the legacy ``/api/`` path (UniFi Controller 5.x–8.x) and
    the modern ``/proxy/network/api/`` path used by UniFi OS devices.
    """

    def __init__(self, base_url, username, password, site='default',
                 verify_ssl=False, unifi_os=False):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.site = site
        self.unifi_os = unifi_os
        self.csrf_token = None

        ctx = ssl.create_default_context()
        if not verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        cookie_handler = urllib.request.HTTPCookieProcessor()
        self._opener = urllib.request.build_opener(
            cookie_handler,
            urllib.request.HTTPSHandler(context=ctx),
        )

    def _request(self, method, path, data=None):
        url = f"{self.base_url}{path}"
        headers = {'Content-Type': 'application/json'}
        if self.csrf_token:
            headers['X-CSRF-Token'] = self.csrf_token

        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, headers=headers,
                                     method=method)
        try:
            with self._opener.open(req) as resp:
                content = resp.read().decode()
                csrf = resp.headers.get('X-CSRF-Token')
                if csrf:
                    self.csrf_token = csrf
                return json.loads(content) if content.strip() else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            raise RuntimeError(
                f"HTTP {exc.code} {exc.reason}: {body}"
            ) from exc

    def login(self):
        """Authenticate against the controller."""
        if self.unifi_os:
            resp = self._request('POST', '/api/auth/login', {
                'username': self.username,
                'password': self.password,
                'remember': False,
            })
            token = (resp.get('csrfToken')
                     or (resp.get('data') or {}).get('csrfToken'))
            if token:
                self.csrf_token = token
        else:
            self._request('POST', '/api/login', {
                'username': self.username,
                'password': self.password,
                'strict': True,
            })

    def logout(self):
        """Log out of the controller (best-effort)."""
        try:
            if self.unifi_os:
                self._request('POST', '/api/auth/logout', {})
            else:
                self._request('POST', '/api/logout', {})
        except RuntimeError:
            pass

    def _site_api(self, method, path, data=None):
        prefix = '/proxy/network' if self.unifi_os else ''
        full_path = f"{prefix}/api/s/{self.site}{path}"
        return self._request(method, full_path, data)

    def create_voucher(self, minutes, amount=1, note='', usage=0,
                       up_kbps=None, down_kbps=None, megabytes=None):
        """Create *amount* vouchers and return the creation timestamp.

        Args:
            minutes:   Validity duration in minutes.
            amount:    Number of vouchers to create.
            note:      Free-text note attached to the vouchers.
            usage:     0 = unlimited uses, 1 = single-use, N = N uses.
            up_kbps:   Upload bandwidth cap in kbps (None = unlimited).
            down_kbps: Download bandwidth cap in kbps (None = unlimited).
            megabytes: Data usage cap in MB (None = unlimited).

        Returns:
            Unix timestamp (int) used to retrieve the vouchers.
        """
        create_time = int(time.time())
        payload = {
            'cmd': 'create-voucher',
            'expire': minutes,
            'n': amount,
            'quota': usage,
            'note': note,
        }
        if up_kbps is not None:
            payload['up'] = up_kbps
        if down_kbps is not None:
            payload['down'] = down_kbps
        if megabytes is not None:
            payload['bytes'] = megabytes

        self._site_api('POST', '/cmd/hotspot', payload)
        return create_time

    def get_vouchers(self, create_time):
        """Return vouchers created at or after *create_time*."""
        resp = self._site_api('GET', f'/stat/voucher?create_time={create_time}')
        return resp.get('data', [])


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_duration(minutes):
    """Return a human-readable duration string for *minutes*."""
    if minutes < 60:
        unit = 'minute' if minutes == 1 else 'minutes'
        return f"{minutes} {unit}"
    if minutes < 1440:
        hours = minutes // 60
        remainder = minutes % 60
        label = f"{hours} {'hour' if hours == 1 else 'hours'}"
        if remainder:
            label += f" {remainder} {'minute' if remainder == 1 else 'minutes'}"
        return label
    days = minutes // 1440
    remainder = minutes % 1440
    label = f"{days} {'day' if days == 1 else 'days'}"
    if remainder:
        hours = remainder // 60
        label += f" {hours} {'hour' if hours == 1 else 'hours'}"
    return label


def format_code(code):
    """Format a raw 10-character voucher code as XXXXX-XXXXX."""
    clean = code.replace(' ', '').replace('-', '')
    if len(clean) >= 10:
        return f"{clean[:5]}-{clean[5:]}"
    return clean


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def build_html(vouchers, title='WiFi Voucher', minutes=60,
               css_file='style.css'):
    """Build a printable HTML page from a list of voucher dicts."""
    validity = f"Valid for {format_duration(minutes)}"

    lines = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '  <meta charset="UTF-8">',
        f'  <title>{escape(title)}</title>',
        f'  <link rel="stylesheet" href="{escape(css_file)}">',
        '</head>',
        '<body>',
    ]

    for v in vouchers:
        code = format_code(v.get('code', ''))

        # Collect optional extra info lines
        extra = []
        up = v.get('up')
        down = v.get('down')
        if down and up:
            extra.append(f'\u2193 {down}\u202fkbps\u2002/\u2002\u2191 {up}\u202fkbps')
        elif down:
            extra.append(f'\u2193 {down}\u202fkbps')
        elif up:
            extra.append(f'\u2191 {up}\u202fkbps')
        if v.get('bytes'):
            extra.append(f"{v['bytes']} MB data limit")
        if v.get('note'):
            extra.append(v['note'])

        lines.append('  <div class="voucher">')
        lines.append('    <div class="header">')
        lines.append(f'      <span class="line1">{escape(title)}</span>')
        lines.append(f'      <span class="line2">{escape(validity)}</span>')
        lines.append('    </div>')
        lines.append(f'    <div class="line3">{escape(code)}</div>')

        if extra:
            lines.append('    <div class="info">')
            for item in extra:
                lines.append(f'      <span class="info-item">{escape(item)}</span>')
            lines.append('    </div>')

        lines.append('  </div>')

    lines.extend(['</body>', '</html>'])
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _env_or_arg(cli_value, env_key, default=None, required=False):
    """Return *cli_value* if given, else the env-var, else *default*."""
    value = cli_value if cli_value is not None else os.environ.get(env_key, default)
    if required and not value:
        flag = '--' + env_key.lower().replace('_', '-')
        print(f"error: {flag} or {env_key} environment variable is required",
              file=sys.stderr)
        sys.exit(1)
    return value


def main():
    parser = argparse.ArgumentParser(
        description='Generate printable UniFi WiFi vouchers.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Credentials can be supplied via CLI flags or environment variables:

  UNIFI_HOST       Controller URL  (e.g. https://192.168.1.1)
  UNIFI_USERNAME   Controller username
  UNIFI_PASSWORD   Controller password
  UNIFI_SITE       Site name (default: default)

Examples:

  python3 generate.py --host https://192.168.1.1 \\
      --username admin --password secret

  python3 generate.py -m 120 -n 20 --note "Conference guests" \\
      --down 10000 --up 5000

  python3 generate.py --unifi-os -m 1440 -n 5 --usage 1
""",
    )

    # Connection
    conn = parser.add_argument_group('connection')
    conn.add_argument('--host', metavar='URL',
                      help='Controller URL (env: UNIFI_HOST)')
    conn.add_argument('--username', metavar='USER',
                      help='Controller username (env: UNIFI_USERNAME)')
    conn.add_argument('--password', metavar='PASS',
                      help='Controller password (env: UNIFI_PASSWORD)')
    conn.add_argument('--site', default=None, metavar='SITE',
                      help='Site name (env: UNIFI_SITE, default: default)')
    conn.add_argument('--unifi-os', action='store_true',
                      help='Use UniFi OS API (Dream Machine, UDM Pro, etc.)')
    conn.add_argument('--verify-ssl', action='store_true',
                      help='Verify SSL certificate (default: off)')

    # Voucher settings
    voucher = parser.add_argument_group('voucher settings')
    voucher.add_argument('-m', '--minutes', type=int, default=60, metavar='N',
                         help='Validity in minutes (default: 60)')
    voucher.add_argument('-n', '--count', type=int, default=10, metavar='N',
                         help='Number of vouchers to generate (default: 10)')
    voucher.add_argument('--note', default='', metavar='TEXT',
                         help='Note attached to each voucher')
    voucher.add_argument('--usage', type=int, default=0, metavar='N',
                         help='Usage limit: 0=unlimited, 1=single-use, '
                              'N=N uses (default: 0)')
    voucher.add_argument('--down', type=int, default=None, metavar='KBPS',
                         help='Download bandwidth limit in kbps')
    voucher.add_argument('--up', type=int, default=None, metavar='KBPS',
                         help='Upload bandwidth limit in kbps')
    voucher.add_argument('--data', type=int, default=None, metavar='MB',
                         help='Data usage limit in MB')

    # Output settings
    output = parser.add_argument_group('output')
    output.add_argument('--title', default='WiFi Voucher', metavar='TEXT',
                        help='Title printed on each voucher card '
                             '(default: "WiFi Voucher")')
    output.add_argument('-o', '--output', default='vouchers.html',
                        metavar='FILE',
                        help='Output HTML file (default: vouchers.html)')
    output.add_argument('--css', default='style.css', metavar='FILE',
                        help='Path to CSS stylesheet (default: style.css)')

    args = parser.parse_args()

    host = _env_or_arg(args.host, 'UNIFI_HOST', required=True)
    username = _env_or_arg(args.username, 'UNIFI_USERNAME', required=True)
    password = _env_or_arg(args.password, 'UNIFI_PASSWORD', required=True)
    site = _env_or_arg(args.site, 'UNIFI_SITE', default='default')

    client = UnifiClient(
        base_url=host,
        username=username,
        password=password,
        site=site,
        verify_ssl=args.verify_ssl,
        unifi_os=args.unifi_os,
    )

    print(f"Connecting to {host} (site: {site})…")
    try:
        client.login()
    except RuntimeError as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Generating {args.count} voucher(s) "
          f"[{format_duration(args.minutes)} validity]…")
    try:
        create_time = client.create_voucher(
            minutes=args.minutes,
            amount=args.count,
            note=args.note,
            usage=args.usage,
            up_kbps=args.up,
            down_kbps=args.down,
            megabytes=args.data,
        )
        vouchers = client.get_vouchers(create_time)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        client.logout()
        sys.exit(1)

    client.logout()

    if not vouchers:
        print("No vouchers returned – check the controller logs.", file=sys.stderr)
        sys.exit(1)

    print(f"Retrieved {len(vouchers)} voucher(s).")

    html = build_html(
        vouchers=vouchers,
        title=args.title,
        minutes=args.minutes,
        css_file=args.css,
    )

    with open(args.output, 'w', encoding='utf-8') as fh:
        fh.write(html)

    print(f"Vouchers written to {args.output}")


if __name__ == '__main__':
    main()
