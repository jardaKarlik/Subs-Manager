"""
Email notifier for scheduled job results.

Sends a concise HTML summary to GMAIL_USER_1 after each incremental run.
Uses the existing Composio Gmail tool (already authenticated) — no new
credentials needed.

Falls back to a no-op (logs only) if Composio is unavailable.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("notifier")


def send_run_summary(
    job_name: str,
    status: str,                    # "ok" | "error" | "skipped"
    stats: dict,                    # free-form {"processed": N, "new": M, ...}
    error: Optional[str] = None,
    started_at: Optional[str] = None,
    duration_s: Optional[float] = None,
) -> bool:
    """
    Send a Gmail notification about a completed scheduled run.

    Returns True if sent, False otherwise (never raises — notification
    failures must not break the scheduler).
    """
    recipient = os.getenv("GMAIL_USER_1", "").strip()
    if not recipient:
        logger.info("[notifier] GMAIL_USER_1 not set — skipping notification")
        return False

    # Build the email body
    status_emoji = {"ok": "✅", "error": "❌", "skipped": "⏭️"}.get(status, "ℹ️")
    subject = f"{status_emoji} Subs-Manager · {job_name} · {status.upper()}"

    stats_rows = "".join(
        f"<tr><td style='padding:4px 12px;color:#555'>{k}</td>"
        f"<td style='padding:4px 12px;font-weight:600'>{v}</td></tr>"
        for k, v in stats.items()
    )

    meta_bits = []
    if started_at:
        meta_bits.append(f"Started: {started_at}")
    if duration_s is not None:
        meta_bits.append(f"Duration: {duration_s:.1f}s")

    meta_html = (
        "<div style='color:#888;font-size:12px;margin-top:16px'>"
        + " · ".join(meta_bits)
        + "</div>"
        if meta_bits
        else ""
    )

    error_html = (
        f"<div style='margin-top:12px;padding:10px;background:#fef2f2;"
        f"border-left:3px solid #dc2626;color:#991b1b;font-size:13px'>"
        f"<b>Error:</b> {error}</div>"
        if error
        else ""
    )

    body_html = f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;
                max-width:520px;margin:0 auto;padding:16px">
      <h2 style="margin:0 0 8px;color:#111">{status_emoji} {job_name}</h2>
      <div style="color:#666;margin-bottom:16px">Status: <b>{status.upper()}</b></div>
      <table style="border-collapse:collapse;width:100%;
                    background:#f9fafb;border-radius:6px">
        {stats_rows}
      </table>
      {error_html}
      {meta_html}
    </div>
    """

    return _send_via_composio(recipient, subject, body_html)


def _send_via_composio(to: str, subject: str, html_body: str) -> bool:
    """Send via Composio's GMAIL_SEND_EMAIL tool. Returns True on success."""
    try:
        import asyncio
        from composio import ComposioToolSet
    except Exception as exc:
        logger.warning(f"[notifier] Composio unavailable: {exc}")
        return False

    api_key = os.getenv("COMPOSIO_API_KEY", "").strip()
    if not api_key:
        logger.info("[notifier] COMPOSIO_API_KEY not set — skipping notification")
        return False

    try:
        toolset = ComposioToolSet(api_key=api_key)
        toolset.execute_action(
            action="GMAIL_SEND_EMAIL",
            params={
                "recipient_email": to,
                "subject": subject,
                "html_body": html_body,
            },
        )
        logger.info(f"[notifier] sent to {to}: {subject}")
        return True
    except Exception as exc:
        logger.warning(f"[notifier] Composio send failed: {exc}")
        return False
