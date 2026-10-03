"""Replace placeholder GCP secrets for the Subscription Manager worker with
the real values from the Railway service environment, then disable the
placeholder version so `latest` resolves to the new one.

Usage:  python scripts/sync_subs_secrets.py <project_id> <service_id> <env_id>
"""

import json
import subprocess
import sys

RAILWAY = "C:/Users/jaros/AppData/Roaming/npm/railway.cmd"
GCLOUD = "gcloud.cmd"


def railway(args):
    return subprocess.check_output([RAILWAY, *args], text=True)


def add_version(secret, value):
    proc = subprocess.run(
        [GCLOUD, "secrets", "versions", "add", secret,
         "--project=43282436639", "--data-file=-"],
        input=value, text=True, check=True, capture_output=True,
    )
    print(proc.stdout.strip())


def disable_version(secret, version):
    subprocess.run(
        [GCLOUD, "secrets", "versions", "disable", str(version),
         f"--secret={secret}", "--project=43282436639"],
        check=True, capture_output=True,
    )


def main():
    project, service, env = sys.argv[1], sys.argv[2], sys.argv[3]
    raw = railway([
        "variable", "list", "--json",
        f"--service={service}", f"--project={project}", f"--environment={env}",
    ])
    vars = json.loads(raw)
    mapping = {
        "subscription_manager_railway_db_url": vars["DATABASE_URL"],
        "subscription_manager_composio_api_key": vars["COMPOSIO_API_KEY"],
        "subscription_manager_imap_server": vars["IMAP_SERVER"],
        "subscription_manager_imap_user": vars["IMAP_USER"],
        "subscription_manager_imap_password": vars["IMAP_PASSWORD"],
        "subscription_manager_wallet_api_token": vars["WALLET_API_TOKEN"],
    }
    for secret, value in mapping.items():
        if not value:
            print(f"SKIP {secret}: missing in Railway service env")
            continue
        print(f"ADD  {secret} (length={len(value)})")
        add_version(secret, value)
        print(f"DIS  {secret} v1")
        disable_version(secret, 1)
    print("done")


if __name__ == "__main__":
    main()