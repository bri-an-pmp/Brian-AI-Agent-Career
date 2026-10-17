# Security

Gradio career assistant (digital twin) deployed to Hugging Face Spaces.

## Reporting a vulnerability

Please report security issues privately through GitHub: **Security → Report a vulnerability** on this repository (private vulnerability reporting is enabled). Don't open a public issue for security problems.

## Automated protections (always on)

| Protection | Status |
|---|---|
| GitHub secret scanning | Enabled |
| Push protection (blocks commits that contain secrets) | Enabled |
| Dependabot vulnerability alerts | Enabled |
| Private vulnerability reporting | Enabled |

## Checks run on 2026-10-16

| Check | Result |
|---|---|
| Secret patterns (AWS, GitHub, OpenAI, Anthropic, Slack, Google, Twilio, Hugging Face keys; private keys; hard-coded tokens) in every file **and every past commit** | ✅ None found |
| Credential files ever committed (`.env`, `*.pem`, `*.key`, `id_rsa`, credentials) | ✅ None found |
| GitHub secret-scanning alerts | ✅ 0 open alerts |
| `.env` excluded from Git | ✅ Listed in `.gitignore`; never committed |
| Personal data in documents | ✅ Resolved on 2026-10-16: `me/Athey_Brian_Resume.pdf` contained a phone number, personal email and internal employer figures; it was replaced with a public version in the current files **and throughout the Git history** |
| Python dependency audit | ⚠️ Not meaningful yet: `requirements.txt` is unpinned. Dependabot alerts are enabled; pinning versions would allow a precise audit. |

## Not covered

These checks are automated and point-in-time. They are not a penetration test or a formal audit.
