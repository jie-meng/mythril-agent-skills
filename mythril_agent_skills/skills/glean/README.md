# Glean Skill

This skill helps AI assistants use Glean CLI (`glean`) for enterprise knowledge workflows:

- Search across company knowledge (documents, wikis, messages)
- Chat with Glean Assistant (AI-powered Q&A)
- Manage AI agents, documents, collections, shortcuts, pins
- Raw authenticated API access to the full Glean REST API

Official Glean CLI repository: https://github.com/gleanwork/glean-cli

## Install Glean CLI (`glean`)

### macOS (recommended)

```bash
brew install gleanwork/tap/glean-cli
```

### Manual install (macOS, Linux, Windows)

```bash
curl -fsSL https://raw.githubusercontent.com/gleanwork/glean-cli/main/install.sh | sh
```

Pre-built binaries for macOS, Linux, and Windows are available on the [Releases](https://github.com/gleanwork/glean-cli/releases) page.

After installation, verify:

```bash
glean --version
```

## Authentication

### OAuth (recommended for interactive use)

```bash
glean auth login    # opens browser, completes PKCE flow
glean auth status   # verify credentials, host, and token expiry
glean auth logout   # remove all stored credentials
```

### API Token (CI/CD)

```bash
export GLEAN_API_TOKEN=your-token
export GLEAN_HOST=your-company-be.glean.com
```

Credentials are resolved in order: environment variables > system keyring > `~/.glean/config.json`.
