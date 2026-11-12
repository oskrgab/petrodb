---
name: orchestrate-issues
description: "Implement a set of GitHub issues with parallel issue-implementer subagents, merged onto one integration branch."
disable-model-invocation: true
---

You are the **orchestrator**. The user points you at a set of GitHub issues: issue numbers, a parent
issue (a PRD whose slices name it under `## Parent`), a label or a milestone. You own the task graph,
the **integration branch** and every merge. `issue-implementer` subagents
(`.claude/agents/issue-implementer.md`) own one issue each. You write no issue code yourself: your
context is for the graph, the merges and the user.

The issues are a **task graph**, not a list. At any moment it has a **frontier**: every issue that is
`ready-for-agent`, has all its blockers `resolved`, and has no implementer running. The whole
frontier runs at once.

All tracker access goes through the `gh` CLI, as `docs/agents/issue-tracker.md` describes. Label names
come from `docs/agents/triage-labels.md`.

## Steps

1. **Read the graph.** Fetch every issue in the set in one call
   (`gh issue list --state all --limit 500 --json number,title,state,labels,body`, filtered to the
   set). An issue's blockers are the `#N` references under its `## Blocked by` heading, plus any native
   links (`gh api repos/{owner}/{repo}/issues/<N>/dependencies/blocked_by --jq '[.[].number]'`).
   Place each issue in exactly one class:
   - **resolved**: closed, or already merged into the integration branch (step 2). Counts as a
     satisfied blocker;
   - **agent**: open and labelled `ready-for-agent`;
   - **human**: open with any other labels, or none. You never spawn these;
   - **stranded**: an agent issue with a human issue somewhere upstream.

   A blocker outside the set counts as resolved when it is closed and as human when it is open. A
   blocker that names an issue that doesn't exist, or a cycle, stops the run: report it. Show the user
   the graph and the classes in a few lines, then carry on without waiting.

2. **Integration branch.** Name it `integration/<slug>`, the slug taken from the parent issue's title,
   or from what the user called the work. If it exists, this is a resumed run: check it out, and treat
   every issue with a `Merge issue #<N>` commit on it as resolved. Otherwise create it from the tip of
   the branch the user is on. Every later step names this branch explicitly; local branches can be
   ahead of `origin`.

3. **Spawn the frontier**, all of it in one message so the implementers run concurrently. Each is an
   `issue-implementer`, in the background, with `isolation: worktree`. Its prompt is the **context
   pointers** and nothing else: the issue number, the integration branch, and the parent issue number
   when there is one. Add a sentence only for what no issue records (a decision the user made in this
   conversation). Model and effort come from the agent definition; pass neither.

4. **Merge each report as it arrives**, one at a time, in arrival order:
   - Merge the issue branch into the integration branch with
     `git merge --no-ff -m "Merge issue #<N>: <title>"`. That subject line is what a resumed run reads
     in step 2. A conflict between two parallel issues is yours when both sides are additive (two
     table entries, two doc sections, two list items): keep both. Anything else goes back to the
     implementer whose branch merges second, by SendMessage, with the conflicting files named.
   - Run the full test suite on the integration branch. On red, reset the integration branch to
     its tip before the merge and send the failing output back to that implementer; merge again when
     they report.
   - Green: the issue is resolved if the implementer ticked every criterion. Leave it open on
     GitHub: it closes when the integration branch lands.
   - Recompute the frontier and spawn what it now holds (step 3) before reading the next report. A
     newly unblocked issue never waits for an unrelated sibling to finish.

5. **Take open points to the user.** An implementer reports a criterion unticked when the issue
   reserves it for the user (a threshold to agree, a schema choice). Bring the user the evidence the
   implementer gathered and your recommendation. Send the decision to the same implementer by
   SendMessage so it finishes the issue with its context intact, then merge as in step 4. Issues
   that don't depend on the answer keep moving meanwhile.

6. **Finish** when the frontier is empty and no implementer is running:
   - Call the Skill tool with `code-review` on the integration branch against the branch it was cut
     from. Give every finding to one `issue-implementer`, then merge and test as in step 4.
   - Remove the implementers' worktrees and delete their merged branches.
   - Leave the integration branch unmerged and unpushed, and the issues open: landing it is the
     user's call. Don't close issues, change labels or open a pull request.

## The final report

- the integration branch, and the full-suite result as you last ran it;
- each issue: `resolved` with its commits, or left open with the reason (human, stranded, open point);
- what the user does next: the human issues, in the order the graph allows, and the command to land
  the branch, with one `Closes #<N>` line per resolved issue for the pull request body. Those close
  the issues when the work reaches the default branch.

## When the agent type is missing

`issue-implementer` is registered at session start. If the Agent tool doesn't list it, spawn
`general-purpose` with `model: opus` and `effort: medium`, and open the prompt with: "Read
`.claude/agents/issue-implementer.md` and follow it as your instructions."
