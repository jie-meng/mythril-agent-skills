# ACLI Command Reference

Install with `brew install acli` (macOS) or https://developer.atlassian.com/cloud/acli/guides/install-acli/.

Login once:

```bash
echo "<api-token>" | acli jira auth login --site "yoursite.atlassian.net" --email "you@example.com" --token
# Or OAuth (opens browser):
acli jira auth login --web
```

After login, no env vars needed. No SSL cert issues.

## View an issue

```bash
acli jira workitem view --key PROJ-123
acli jira workitem view --key "PROJ-123,PROJ-456"
```

## Search issues via JQL

```bash
acli jira workitem search --jql "project=PROJ AND status='In Progress'"
acli jira workitem search --jql "assignee=currentUser() AND status!=Done" --limit 30
acli jira workitem search --jql "project=PROJ AND created >= -7d ORDER BY created DESC"
acli jira workitem search --jql "summary ~ 'login bug' AND priority=High"
```

## Create an issue

```bash
acli jira workitem create --summary "Fix login timeout" --project PROJ --type Bug
acli jira workitem create --summary "Add export feature" --project PROJ --type Story \
  --description "Users should be able to export data as CSV" \
  --priority High --label "feature,backend" --parent PROJ-100
```

## Edit an issue

```bash
acli jira workitem edit --key PROJ-123 --summary "Updated summary" --priority High
acli jira workitem edit --key "PROJ-123,PROJ-456" --label "urgent,backend"
```

## Assign an issue

```bash
acli jira workitem assign --key PROJ-123 --user 5b10ac8d82e05b22cc7d4ef5
acli jira workitem assign --key PROJ-123 --user none
```

## Transition (move) an issue

Transitions by status name (not ID). To see available statuses, view the issue first.

```bash
acli jira workitem transition --key PROJ-123 --status "In Progress"
acli jira workitem transition --key PROJ-123 --status Done --comment "Work complete"
```

## Comment on an issue

```bash
acli jira workitem comment-create --key PROJ-123 --body "Investigating the root cause now."
```

## List comments

```bash
acli jira workitem comment-list --key PROJ-123
```

## Link two issues

```bash
acli jira workitem link --type Relates --inward PROJ-456 --outward PROJ-123
```

## List boards / sprints / sprint issues

```bash
acli jira board list --project PROJ
acli jira sprint list --board-id 42 --state active
acli jira sprint issue-list --sprint-id 123
```

## Current user info

```bash
acli jira auth status
```
