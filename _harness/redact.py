"""Masking for anything a demo prints.

A demo is usually run on a shared screen, and the interesting output — the
client's `base_url`, its injected headers, the exception a rejection produced —
is exactly the output that carries the gateway hostname, the consumer
credentials, and the tenant's infrastructure identifiers. So demos never print
those values directly; they print them through here.

Redaction is **on by default** and is switched off only by setting
`DEMO_REDACT=0`, which the preflight banner then says out loud so nobody
un-redacts, forgets, and starts recording.

Three things get masked:

* **Credentials** — the `client_id`/`client_secret` header pair, bearer tokens,
  API keys. Replaced entirely; the length is shown so "it is set" stays visible.
* **Hostnames** — the ingress host of the governed proxy. The *path* survives,
  because "note there is no `/v1`" is a teaching point and the path shape is not
  the sensitive part. Loopback addresses are left alone: pointing at the local
  simulator is something you want the audience to see.
* **Tenant identity from live captures** — `x-envoy-decorator-operation` embeds
  the Anypoint API-instance and environment ids, and `openai-organization` /
  `openai-project` / `cf-ray` identify the account behind the proxy. These ride
  along in captured fixtures and would otherwise be printed verbatim.

Header names are always shown. The lesson is *which* headers the SDK injects;
their values are never the lesson.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping

__all__ = [
    "enabled",
    "headers",
    "secret",
    "text",
    "url",
    "why_visible",
]

# Values are replaced wholesale — these authenticate you.
_SECRET_HEADERS = frozenset(
    {
        "client_id",
        "client_secret",
        "authorization",
        "proxy-authorization",
        "api-key",
        "x-api-key",
        "openai-api-key",
    }
)

# Values identify the tenant or the account behind the gateway.
_IDENTITY_HEADERS = frozenset(
    {
        "x-envoy-decorator-operation",
        "openai-organization",
        "openai-project",
        "cf-ray",
        "x-request-id",
        "x-correlation-id",
    }
)

_LOOPBACK = ("127.0.0.1", "localhost", "0.0.0.0", "::1")

# Reserved-for-documentation names (RFC 2606 / RFC 6761). These can never resolve
# to a real host, so masking them would hide the fact that a value is a
# deliberate placeholder — which is the opposite of what masking is for.
_NEVER_REAL = (".invalid", ".example", ".test", ".localhost", "example.com", "example.org")

_URL_RE = re.compile(r"(?P<scheme>https?://)(?P<host>[^/\s]+)")
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
)
_INSTANCE_RE = re.compile(r"api-instance-\d{4,}", re.IGNORECASE)

_MASK = "<redacted>"
_HOST_MASK = "<redacted-host>"


def enabled() -> bool:
    """Whether masking is active. On unless `DEMO_REDACT` is explicitly falsey."""
    return os.environ.get("DEMO_REDACT", "1").strip().lower() not in ("0", "false", "no", "off")


def why_visible() -> str | None:
    """The warning to show when masking has been switched off, or `None`."""
    if enabled():
        return None
    return (
        "DEMO_REDACT=0 — output is UNMASKED and will show your gateway host, "
        "credentials and tenant identifiers. Do not screen-share or record."
    )


def _is_loopback(host: str) -> bool:
    """Whether a host is safe to show: loopback, or reserved for documentation."""
    bare = host.split(":", 1)[0].strip("[]").lower()
    return bare in _LOOPBACK or any(bare.endswith(suffix) for suffix in _NEVER_REAL)


def url(value: str | None) -> str:
    """A URL with its host masked and its path kept.

    Loopback URLs pass through untouched — `http://127.0.0.1:8080` is the local
    simulator, and showing it is the point of the offline demos.
    """
    if value is None:
        return "<unset>"
    value = str(value)
    if not enabled():
        return value

    def _sub(m: re.Match[str]) -> str:
        host = m.group("host")
        if _is_loopback(host):
            return m.group(0)
        return f"{m.group('scheme')}{_HOST_MASK}"

    return _URL_RE.sub(_sub, value)


def secret(value: str | None, *, show_length: bool = True) -> str:
    """A credential, replaced entirely.

    The length is kept by default so "configured" stays distinguishable from
    "empty" — the single most common thing to debug on stage.
    """
    if value is None:
        return "<unset>"
    if not enabled():
        return str(value)
    if not value:
        return "<empty>"
    return f"{_MASK} ({len(str(value))} chars)" if show_length else _MASK


def text(value: object) -> str:
    """Scrub a free-form string: exception messages, log lines, response bodies.

    Beyond the generic URL/UUID/instance-id patterns this also removes the
    *configured* credential values by exact substring, so a message that
    interpolated the real client secret cannot slip through just because it did
    not match a pattern.
    """
    out = str(value)
    if not enabled():
        return out

    for var in (
        "DONKEY_LLM_PROXY_CLIENT_SECRET",
        "DONKEY_LLM_PROXY_CLIENT_ID",
        "DONKEY_LLM_PROXY_KEY",
        "ANYPOINT_CLIENT_SECRET",
        "ANYPOINT_CLIENT_ID",
        "ANYPOINT_ORG_ID",
    ):
        configured = os.environ.get(var)
        if configured and len(configured) >= 4:
            out = out.replace(configured, _MASK)

    proxy = os.environ.get("DONKEY_LLM_PROXY_URL")
    if proxy:
        out = out.replace(proxy, url(proxy))
        host = _URL_RE.match(proxy)
        if host and not _is_loopback(host.group("host")):
            out = out.replace(host.group("host"), _HOST_MASK)

    out = _URL_RE.sub(lambda m: url(m.group(0)), out)
    out = _INSTANCE_RE.sub(_MASK, out)
    return _UUID_RE.sub(_MASK, out)


def headers(
    mapping: Mapping[str, str] | Iterable[tuple[str, str]] | None,
) -> dict[str, str]:
    """Header names verbatim, values masked by classification.

    Credential headers are replaced, tenant-identity headers are replaced, and
    everything else passes through `text()` — so `x-token-*`,
    `x-llm-proxy-*`, `www-authenticate`, `x-injection-protection` and
    `x-donkey-simulator` stay readable, because those are the demo.
    """
    if mapping is None:
        return {}
    items = mapping.items() if isinstance(mapping, Mapping) else mapping
    out: dict[str, str] = {}
    for name, value in items:
        # Classify on the last dotted segment as well as the whole name, so a
        # flattened nested key like `default_headers.client_secret` is still
        # recognised as the credential it is.
        full = str(name).lower()
        key = full.rsplit(".", 1)[-1]
        if not enabled():
            out[str(name)] = str(value)
        elif key in _SECRET_HEADERS or full in _SECRET_HEADERS:
            out[str(name)] = secret(str(value))
        elif key in _IDENTITY_HEADERS or full in _IDENTITY_HEADERS:
            out[str(name)] = _MASK
        else:
            out[str(name)] = text(value)
    return out
