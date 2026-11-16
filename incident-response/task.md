The Woodshed alert "Practice sessions failing" is firing. You are on call for incident {id}.

The incident directory is `incident-response/incidents/{id}/`. It holds `alert.json`, the Grafana webhook, and `evidence.json`, the Loki error logs and Tempo traces of failing `/api/sessions*` requests over the alert window.

Follow your instructions as the on-call agent, with these specifics:

1. Run `git branch --show-current` first. That branch is what's running: base your fix and your PR on it. If it starts with `drill-`, this is an incident drill: start the PR title with `[drill]` and say so at the top of its body.
2. Branch with `git switch -c incident-{id}`.
3. Diagnose with the evidence and Grafana (read-only), reproduce with a failing test, fix, then run `make lint` and `make test`.
4. Write `incident-response/incidents/{id}/report.md` and commit it with `alert.json`, `evidence.json` and the fix.
5. Push with `git push -u origin incident-{id}` and open the PR with `gh pr create --base <the branch from step 1> --title "fix: <symptom> (incident {id})" --body-file <file>`, writing the body to a file outside the repo (you can't delete files). The body links the report.

Your tools are a fixed allowlist: you can't merge, deploy, force-push or dispatch workflows. If something you need is denied, say so in the report instead of working around it.
