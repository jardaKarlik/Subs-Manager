#!/usr/bin/env python3
"""
Composio Unified Connection Test
Tests ALL data sources through Composio:
  - Gmail (j.karleek@gmail.com)
  - Outlook/Live.com (jaroslav.karlik@live.com)
  - IMAP (karlik@klikni.org via Composio)
  - Reddit
  - LinkedIn

Usage:
  python test_composio_unified.py            # Full test
  python test_composio_unified.py --sources  # List sources only
  python test_composio_unified.py --quick    # Quick connection check only
"""

import os, sys, json, requests, imaplib, ssl
from datetime import datetime
from dotenv import load_dotenv

API_BASE = "https://backend.composio.dev/api/v1"
load_dotenv()


def get_headers():
    api_key = os.getenv("COMPOSIO_API_KEY")
    if not api_key or api_key == "comp_your_api_key_here":
        print("  [FAIL] COMPOSIO_API_KEY not set or placeholder.")
        print("         Set it in .env file.")
        sys.exit(1)
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def test_api_connection():
    """Verify that the Composio API is reachable and the key is valid."""
    print("\n" + "=" * 60)
    print("  [1] COMPOSIO API CONNECTION")
    print("=" * 60)
    try:
        resp = requests.get(f"{API_BASE}/connectedAccounts", headers=get_headers(), timeout=15)
        if resp.status_code == 200:
            print("  [OK]  Composio API is reachable and key is valid.")
            return True
        print(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:200]}")
        return False
    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot reach backend.composio.dev - check internet.")
        return False
    except requests.exceptions.Timeout:
        print("  [FAIL] Request timed out.")
        return False


def list_connected_accounts():
    """List every account connected via Composio and categorise them."""
    print("\n" + "=" * 60)
    print("  [2] CONNECTED ACCOUNTS")
    print("=" * 60)
    try:
        resp = requests.get(f"{API_BASE}/connectedAccounts", headers=get_headers(), timeout=15)
        if resp.status_code != 200:
            print(f"  [FAIL] HTTP {resp.status_code}")
            return {}
        accounts = resp.json()
        print(f"  Total connected: {len(accounts)}\n")
        cat = {"gmail": [], "outlook": [], "imap": [], "reddit": [], "linkedin": [], "other": []}
        for a in accounts:
            app = a.get("appName", "?").lower()
            sid = a.get("id", "?")
            st = a.get("status", "?")
            em = a.get("email", "")
            line = f"    {app:<20} id={sid:<20} status={st}"
            if em:
                line += f"  ({em})"
            print(line)
            if "gmail" in app:
                cat["gmail"].append(a)
            elif "outlook" in app or "microsoft" in app or "live" in app:
                cat["outlook"].append(a)
            elif "imap" in app or "zoner" in app:
                cat["imap"].append(a)
            elif "reddit" in app:
                cat["reddit"].append(a)
            elif "linkedin" in app:
                cat["linkedin"].append(a)
            else:
                cat["other"].append(a)
        return cat
    except Exception as e:
        print(f"  [FAIL] {e}")

def test_gmail(accounts):
    """Test the first connected Gmail account and fetch 5 recent messages."""
    print("\n" + "=" * 60)
    print("  [3] GMAIL (via Composio)")
    print("=" * 60)
    if not accounts.get("gmail"):
        print("  [SKIP] No Gmail account connected in Composio.")
        return
    acc = accounts["gmail"][0]
    cid = acc.get("id")
    print(f"  Account: {acc.get('email', 'N/A')}  (connection id={cid})")
    h = get_headers()
    try:
        r = requests.post(f"{API_BASE}/actions/execute", headers=h,
            json={"connectedAccountId": cid, "actionName": "gmail_get_profile", "input": {}},
            timeout=15)
        if r.status_code == 200:
            d = r.json()
            print(f"  [OK]   Profile: msgs={d.get('data',{}).get('messagesTotal','?')}, "
                  f"threads={d.get('data',{}).get('threadsTotal','?')}")
        else:
            print(f"  [WARN] Profile fetch: HTTP {r.status_code}")
        print("  Fetching 5 recent messages ...")
        r = requests.post(f"{API_BASE}/actions/execute", headers=h,
            json={"connectedAccountId": cid, "actionName": "gmail_fetch_emails",
                  "input": {"max_results": 5}},
            timeout=20)
        if r.status_code == 200:
            msgs = r.json().get("data", {}).get("messages", [])
            print(f"  [OK]   Fetched {len(msgs)} messages\n")
            for i, m in enumerate(msgs, 1):
                print(f"    {i:>2}. {m.get('from','N/A'):35s} | {m.get('subject',m.get('snippet','N/A'))[:70]}")
        else:
            print(f"  [WARN] Fetch failed: HTTP {r.status_code}")
    except Exception as e:
        print(f"  [FAIL] {e}")


def test_outlook(accounts):
    """Test the first connected Outlook/Microsoft account."""
    print("\n" + "=" * 60)
    print("  [4] OUTLOOK / LIVE.COM (via Composio)")
    print("=" * 60)
    if not accounts.get("outlook"):
        print("  [SKIP] No Outlook/Microsoft account connected in Composio.")
        return
    acc = accounts["outlook"][0]
    cid = acc.get("id")
    print(f"  Account: {acc.get('email', 'N/A')}  (connection id={cid})")
    h = get_headers()
    print("  Fetching 5 recent emails ...")
    try:
        r = requests.post(f"{API_BASE}/actions/execute", headers=h,
            json={"connectedAccountId": cid, "actionName": "outlook_query_emails",
                  "input": {"limit": 5}},
            timeout=20)
        if r.status_code == 200:
            msgs = r.json().get("data", {}).get("value", [])
            print(f"  [OK]   Fetched {len(msgs)} emails\n")
            for i, m in enumerate(msgs, 1):
                s = m.get("from", {}).get("emailAddress", {}).get("address", "N/A")
                subj = m.get("subject", "N/A")[:70]
                d = m.get("receivedDateTime", "N/A")[:19]
                print(f"    {i:>2}. {s:35s} | {d} | {subj}")
        else:
            print(f"  [FAIL] HTTP {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"  [FAIL] {e}")


def test_imap(accounts):
    """Test IMAP mailbox (karlik@klikni.org) via Composio or direct IMAP."""
    print("\n" + "=" * 60)
    print("  [5] IMAP - KLIKNI.ORG")
    print("=" * 60)
    if accounts.get("imap"):
        acc = accounts["imap"][0]
        print(f"  Composio IMAP connection found: id={acc.get('id')}")
        h = get_headers()
        try:
            r = requests.post(f"{API_BASE}/actions/execute", headers=h,
                json={"connectedAccountId": acc.get("id"),
                      "actionName": "imap_list_mailboxes", "input": {}},
                timeout=15)
            if r.status_code == 200:
                mboxes = r.json().get("data", [])
                print(f"  [OK]   Composio IMAP works! {len(mboxes)} mailboxes")
                for mb in mboxes[:5]:
                    print(f"         - {mb}")
                return
            print(f"  [WARN] Composio IMAP failed (HTTP {r.status_code}) - trying direct ...")
        except Exception as e:
            print(f"  [WARN] Composio IMAP error: {e} - trying direct ...")
    else:
        print("  No Composio IMAP connection - trying direct IMAP ...")
    _test_imap_direct()


def _test_imap_direct():
    """Direct IMAP test for karlik@klikni.org (Zoner)."""
    server = os.getenv("IMAP_SERVER", "imap.zoner.com")
    port = int(os.getenv("IMAP_PORT", "993"))
    user = os.getenv("IMAP_USER", "")
    pw = os.getenv("IMAP_PASSWORD", "")
    if not user or not pw:
        print("  [SKIP] IMAP_USER/PASSWORD not set in .env")
        return
    ctx = ssl.create_default_context()
    if os.getenv("IMAP_VERIFY_SSL", "true").lower() in ("false", "0", "no"):
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with imaplib.IMAP4_SSL(server, port, ssl_context=ctx) as mail:
            mail.login(user, pw)
            _, c = mail.select("INBOX")
            total = int(c[0]) if c else 0
            print(f"  [OK]   Connected {user} @ {server}, INBOX: {total} msgs")
            _, ids = mail.search(None, "ALL")
            if ids[0]:
                for mid in ids[0].split()[-3:]:
                    _, d = mail.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
                    if d[0][1]:
                        print(f"         {d[0][1].decode('utf-8','ignore').strip()}")
            mail.logout()
    except imaplib.IMAP4.error as e:
        print(f"  [FAIL] IMAP login error: {e}")
    except Exception as e:
        print(f"  [FAIL] {e}")


def test_reddit(accounts):
    """Test the Reddit connection via Composio."""
    print("\n" + "=" * 60)
    print("  [6] REDDIT (via Composio)")
    print("=" * 60)
    if not accounts.get("reddit"):
        print("  [SKIP] No Reddit account connected in Composio.")
        return
    cid = accounts["reddit"][0].get("id")
    print(f"  Account id={cid}")
    h = get_headers()
    try:
        r = requests.post(f"{API_BASE}/actions/execute", headers=h,
            json={"connectedAccountId": cid, "actionName": "reddit_get_identity", "input": {}},
            timeout=15)
        if r.status_code == 200:
            print(f"  [OK]   Reddit identity: {str(r.json().get('data',{}))[:100]}")
        else:
            print(f"  [WARN] Reddit action: HTTP {r.status_code}")
            rr = requests.get(f"{API_BASE}/apps/reddit/actions", headers=h, timeout=10)
            if rr.status_code == 200:
                actions = rr.json()
                names = [a.get("name") for a in
                         (actions if isinstance(actions,list) else actions.get("items",[]))][:5]
                print(f"         Available actions: {', '.join(names)}")
    except Exception as e:
        print(f"  [FAIL] {e}")


def test_linkedin(accounts):
    """Test the LinkedIn connection via Composio."""
    print("\n" + "=" * 60)
    print("  [7] LINKEDIN (via Composio)")
    print("=" * 60)
    if not accounts.get("linkedin"):
        print("  [SKIP] No LinkedIn account connected in Composio.")
        return
    cid = accounts["linkedin"][0].get("id")
    print(f"  Account id={cid}")
    h = get_headers()
    try:
        r = requests.post(f"{API_BASE}/actions/execute", headers=h,
            json={"connectedAccountId": cid, "actionName": "linkedin_get_profile", "input": {}},
            timeout=15)
        if r.status_code == 200:
            print(f"  [OK]   LinkedIn profile: {str(r.json().get('data',{}))[:100]}")
        else:
            print(f"  [WARN] LinkedIn action: HTTP {r.status_code}")
            rr = requests.get(f"{API_BASE}/apps/linkedin/actions", headers=h, timeout=10)
            if rr.status_code == 200:
                actions = rr.json()
                names = [a.get("name") for a in
                         (actions if isinstance(actions,list) else actions.get("items",[]))][:5]
                print(f"         Available actions: {', '.join(names)}")
    except Exception as e:
        print(f"  [FAIL] {e}")


def list_available_apps():
    """Show which email/social integrations Composio offers."""
    print("\n" + "=" * 60)
    print("  [8] AVAILABLE COMPOSIO APPS (email & social)")
    print("=" * 60)
    try:
        r = requests.get(f"{API_BASE}/apps", headers=get_headers(), timeout=15)
        if r.status_code != 200:
            print(f"  [FAIL] HTTP {r.status_code}")
            return
        apps = r.json()
        targets = ["gmail", "outlook", "microsoft", "mail", "imap",
                    "reddit", "linkedin", "exchange", "office"]
        found = {}
        for app in apps:
            name = app.get("name", "")
            key = name.lower()
            for t in targets:
                if t in key:
                    found.setdefault(t, []).append(name)
        for cat, names in sorted(found.items()):
            print(f"    {cat:<12} {', '.join(names)}")
        print(f"\n  ({len(apps)} total apps available in Composio)")
    except Exception as e:
        print(f"  [FAIL] {e}")


def main():
    print("=" * 60)
    print("  UNIFIED CONNECTION TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    flags = set(sys.argv[1:])
    quick = "--quick" in flags
    sources_only = "--sources" in flags

    api_ok = test_api_connection()
    accounts = {} if not api_ok else list_connected_accounts()

    if quick:
        print("\n" + ("=" * 60))
        print("  QUICK CHECK RESULT")
        print("=" * 60)
        print(f"  Composio API:    {'[OK]' if api_ok else '[FAIL]'}")
        imap_ok = bool(os.getenv("IMAP_USER") and os.getenv("IMAP_PASSWORD"))
        print(f"  IMAP configured: {'[OK]' if imap_ok else '[SKIP]'}")
        print()
        return

    # Always test IMAP direct (Composio or not)
    if not api_ok:
        print("\n  [INFO] Composio API unavailable - testing IMAP directly ...")
        print("  [INFO] Get a fresh API key at https://app.composio.dev/settings")

    if sources_only:
        test_imap(accounts)
        return

    test_gmail(accounts)
    test_outlook(accounts)
    test_imap(accounts)
    test_reddit(accounts)
    test_linkedin(accounts)
    if api_ok:
        list_available_apps()

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    src = {
        "composio_api": api_ok,
        "gmail":        bool(accounts.get("gmail")),
        "outlook":      bool(accounts.get("outlook")),
        "imap_direct":  bool(os.getenv("IMAP_USER") and os.getenv("IMAP_PASSWORD")),
        "imap_via_composio": bool(accounts.get("imap")),
        "reddit":       bool(accounts.get("reddit")),
        "linkedin":     bool(accounts.get("linkedin")),
    }
    for k, v in src.items():
        print(f"    {k:<20} {'[OK]' if v else '[WARN]'}")
    print()
    if not api_ok:
        print("  ! Composio API key appears expired or invalid.")
        print("  ! Get a new one at https://app.composio.dev/settings")
        print()
    print("  Next steps:")
    print("    1. Renew API key at https://app.composio.dev")
    print("    2. Connect Reddit & LinkedIn in Composio dashboard")
    print("    3. Run email parsing: python email_fetcher.py")
    print("    4. Start API server: python api.py\n")

    report = {"timestamp": datetime.now().isoformat(), "composio_api_ok": api_ok,
              "connected_accounts": sum(len(v) for v in accounts.values()), "sources": src}
    with open("connection_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("  Report saved to connection_report.json")

if __name__ == "__main__":
    main()
