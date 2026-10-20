# Tooling Notes

- This environment's interactive shell is Bash. Use Bash syntax and commands (`&&`, `sleep`, `grep`, etc.); do not assume PowerShell parsing or aliases.
- For Railway project work, prefer explicit project/environment/service IDs. Verify mutations with Railway status/logs.
- Never put Railway, Discord, or other credentials in source files or Docker images. Read credentials from GCP Secret Manager and inject them through Railway variables.
