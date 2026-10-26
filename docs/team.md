# Agent team

Woodshed is built by five Claude Code subagents (`.claude/agents/`) and one human. Each agent has one job and only the tools that job needs. Work moves between them through GitHub Issues and PRs, so every handoff is visible on the tracker.

## Roles

| Role | Job | Input → Output | Tools |
| --- | --- | --- | --- |
| **planner** | Turns the spec into small issues with testable acceptance criteria. Orders them by dependency. | `docs/plans.md` → issues | Read, `gh issue` |
| **tester** | Writes failing tests from an issue's acceptance criteria | Issue → tests on the issue branch | Read/write tests, Bash, Context7 |
| **implementer** | Writes the minimum code that makes the tests pass, then opens the PR | Branch with tests → PR | Read/write, Bash, Context7, Playwright |
| **reviewer** | Checks the PR against the acceptance criteria, the spec and the code style | PR → verdict comment | Read-only, `gh pr`, Playwright, `/code-review` |
| **on-call** | Responds to production alerts: diagnoses, fixes, opens a PR | Alert + evidence → fix PR + report | Read/write, Bash, Grafana MCP (read-only) |
| **human** | Sets priorities, merges PRs, approves prod deploys, holds the secrets | PR → merge | Everything |

## Flow

```
plans.md ─▶ planner ─▶ issue #n
                          │
                          ▼
              tester: branch n-slug, failing tests
                          │
                          ▼
           implementer: code, make test green, PR "Closes #n"
                          │
                          ▼
         reviewer: verdict ──changes──▶ implementer
                          │ approve
                          ▼
                human merges ─▶ CI/CD deploys to dev

Grafana alert ─▶ responder ─▶ on-call: fix PR ─▶ reviewer ─▶ human
```

## Handoffs

Every agent comments on the issue when it finishes, so the tracker shows who did what:

```
**tester:** 6 failing tests in backend/tests/unit/test_scheduler.py (box transitions, cap, ordering). Ready for implementer.
**implementer:** PR #31 open. make test green. Ready for review.
**reviewer:** Approve. All 4 acceptance criteria met; one style nit inline.
```

- **The tester skips** issues with no testable behavior, such as docs or config. It says so in its comment.
- **A reviewer verdict** is one of: **approve**, or **changes requested** with a numbered list. Agents share the human's GitHub account and can't formally approve their own PRs, so the verdict is a PR comment.
- **When an agent is blocked** by an unclear spec or a missing dependency, it comments on the issue with a question and stops.

## Guardrails

- Only the human merges and deploys to prod. `.claude/settings.json` denies `gh pr merge`, force pushes and manual workflow dispatches for every agent. Branch protection on `main` requires CI to pass.
- The reviewer has no write tools. The on-call agent's Grafana access is read-only (`--disable-write`).
- Secrets live in GitHub and Render, never in the repo or in an agent's prompt.

## Parallel work

Independent issues run in parallel, each agent in its own git worktree (`isolation: worktree`). Issues are grouped into waves by dependency:

| Wave | Issues |
| --- | --- |
| 0 | #1 → #2 → #3 (sequential: they set the conventions) |
| 1 | #4, #5, #7, #8, #16, #17 |
| 2 | #6, #9, #10 |
| 3 | #11, #12, #13, #14 |
| 4 | #15, #18–#21, #22 |
| 5 | #23–#28 |

A wave starts when the wave before it is merged. Within a wave, agents touch disjoint files.

## Definition of done

- All acceptance criteria are ticked in the PR.
- `make lint` and `make test` pass locally and in CI.
- The reviewer approved it, and the human merged it.
