# Jenkins REST API Reference

Cheat sheet for operations beyond `scripts/jenkins_api.py`. All examples
assume the environment variables from `README.md` and use `$JENKINS_URL`.

## Authentication

HTTP Basic with `JENKINS_USER:JENKINS_API_TOKEN`:

```bash
curl -u "$JENKINS_USER:$JENKINS_API_TOKEN" "$JENKINS_URL/api/json"
```

- API-token auth bypasses CSRF crumbs on Jenkins 2.96+ (2017). If your
  instance disables the exemption, fetch a crumb and send it:

```bash
curl -sS -u "$JENKINS_USER:$JENKINS_API_TOKEN" "$JENKINS_URL/crumbIssuer/api/json"
# → {"_class":"...","crumb":"abc123","crumbRequestField":"Jenkins-Crumb"}
# Send: -H "Jenkins-Crumb: abc123" and the session cookie from the same response
```

## Job and build endpoints

Job names nest through folders: job `team/services/deploy` lives at
`/job/team/job/services/job/deploy`.

| Operation | Endpoint |
|---|---|
| Instance info / job list | `GET /api/json?tree=jobs[name,color,url]` |
| Job details | `GET /job/<name>/api/json` |
| Build details | `GET /job/<name>/<n>/api/json` |
| Latest build | `GET /job/<name>/lastBuild/api/json` |
| All builds (paginated) | `GET /job/<name>/api/json?tree=builds[number,result,timestamp]{0,50}` |
| Queue status | `GET /queue/api/json` |
| Queue item | `GET /queue/item/<id>/api/json` |
| Pipeline stages | `GET /job/<name>/<n>/wfapi/describe` |
| Console text | `GET /job/<name>/<n>/consoleText` |
| Incremental console | `GET /job/<name>/<n>/logText/progressiveText?start=<offset>` |
| Trigger build | `POST /job/<name>/build` |
| Trigger parameterized | `POST /job/<name>/buildWithParameters` (form fields) |
| Abort build | `POST /job/<name>/<n>/stop` |
| Who am I | `GET /whoAmI/api/json` |

### The `tree` parameter

`api/json` responses are large; `tree` selects fields. Ranges `{0,200}` cap
list sizes, brackets nest:

```
?tree=jobs[name,color,lastBuild[number,result]]{0,200}
?tree=property[parameterDefinitions[name,type,defaultParameterValue[value]]]
```

### Triggering builds

A parameterless job takes `POST /job/<name>/build` → `201 Created` with a
`Location: .../queue/item/<id>/` header. A parameterized job takes
`POST /job/<name>/buildWithParameters` with form-encoded fields:

```bash
curl -sS -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  -X POST "$JENKINS_URL/job/deploy/buildWithParameters" \
  --data-urlencode "TARGET_SERVERS=172.22.193.101" \
  --data-urlencode "SERVER_VERSION=latest" -D - -o /dev/null
```

Queue item JSON gains `executable: {number, url}` once the build starts; the
item disappears from `/queue/item/<id>` after leaving the queue.

### Incremental console reading

`logText/progressiveText` returns the log slice from `start` and reports
progress in response headers:

- `X-Text-Size` — new total byte offset (feed back as the next `start`)
- `X-More-Data` — `true` while the log is still growing

Poll in a loop; combine with `GET /job/<name>/<n>/api/json?tree=building,result`
to detect completion. `consoleText` is the simple full-text variant.

### Remote-trigger tokens (alternative auth)

Jobs can enable a "Trigger builds remotely" token that allows
`GET /job/<name>/build?token=<job-token>` without user credentials. The
bundled script does not use this; it is useful for cron/webhook integration.

## Job types

- **Pipeline (workflow)** jobs expose `/wfapi/describe` with
  `stages[].name/status/durationMillis` (status: `SUCCESS`, `FAILED`,
  `ABORTED`, `IN_PROGRESS`, `PAUSED_PENDING_INPUT`, `SKIPPED`).
- **Freestyle / matrix** jobs have no stage API — use `consoleText`.

## Status colors

Job `color` field: `blue` (stable), `red` (failed), `yellow` (unstable),
`aborted`, `notbuilt`, `disabled`; suffix `_anime` means a build is running.

## Useful instance-level endpoints

| Operation | Endpoint |
|---|---|
| Plugins | `GET /pluginManager/api/json?tree=plugins[shortName,version]` |
| Nodes/agents | `GET /computer/api/json?tree=computer[displayName,offline]` |
| Create/replace job config | `POST /job/<name>/config.xml` (XML body, `Content-Type: text/xml`) |
| Reload config from disk | `POST /reload` |
| Safe restart | `POST /safeRestart` (script does not use this) |
