# Security Policy

## Reporting a vulnerability

Please do not report security problems in public issues or pull requests.

Use GitHub's private reporting: open the repository's **Security** tab and choose **Report a vulnerability**. If that is not available, email asifanwar0705@gmail.com with the subject "Market Scout security".

Include what you found, the steps to reproduce it, and the version or commit you tested. You should get a reply within a few days. Please give us reasonable time to fix the problem before you disclose it.

## What is in scope

- Authentication, refresh tokens and role checks
- API keys and the public API
- Webhook signing
- Stored credentials (Google service account, paid source keys, Anthropic key)
- Do-not-contact enforcement
- Fetching of public websites (the app must only visit public addresses)

## Running your own copy safely

- Set a strong `SECRET_KEY` in the backend `.env`. Never commit `.env`.
- Keep the database file and the `secrets/` folder out of version control and off public hosting.
- Serve the app over HTTPS and set `CORS_ORIGINS` to your real front-end address only.
