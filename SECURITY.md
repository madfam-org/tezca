# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Tezca, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email security@madfam.io with details
3. Include steps to reproduce if possible
4. We will acknowledge receipt within 48 hours

## Sensitive Data

This project handles sensitive Mexican legal data including:
- Laws, regulations, and jurisprudence
- PopularLaws API keys and access tokens
- User search history and preferences
- Cached legal document content

### Rules

- API keys and tokens must **never** be committed to version control
- User search history must be stored encrypted at rest
- All API endpoints require authentication
- Logs must never contain passwords, tokens, or user search queries

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
