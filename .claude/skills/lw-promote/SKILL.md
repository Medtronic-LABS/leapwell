---
name: lw-promote
description: Promote an agreed LeapWell Discussion (idea, field feedback, partner request) to a feature issue in Medtronic-LABS/leapwell - read the discussion, run the lw-ticket feature interview for the gaps, privacy-scrub, preview, create on an explicit yes, and comment on the discussion with the issue link.
argument-hint: <discussion-number>
disable-model-invocation: true
---

# Promote Discussion #$ARGUMENTS

Ideas live in leapwell Discussions; agreed ones become `type:feature` issues. Process reference: `docs/process/SDLC.md`.

1. **Read the discussion.** If no number was given, ask for one.
   ```
   gh api graphql -F owner=Medtronic-LABS -F name=leapwell -F number=$ARGUMENTS -f query='query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){discussion(number:$number){id title body url category{name} comments(first:50){nodes{body}}}}}'
   ```
   Keep the discussion `id` (for step 6) and `url`. Summarise it in 3-5 lines and ask the PM to confirm it has been agreed for promotion.

2. **Duplicate check.** `gh issue list --repo Medtronic-LABS/leapwell --state open --search '<2-3 keywords>' --limit 5 --json number,title,url`. If one matches, offer to comment the discussion link on it instead (preview, yes) and stop.

3. **Fill the feature contract.** Read `.claude/skills/lw-ticket/references/feature.md`. Derive every field you can from the discussion and comments (User, Problem, Proposed solution, Acceptance criteria, Programme, Offline behaviour, Designs); then ask only for the gaps, one question at a time, as that file says. Draft acceptance criteria yourself and confirm them. Add a section at the end:
   ```markdown
   ### Source

   Promoted from <discussion url>
   ```

4. **Privacy scrub.** Apply `.claude/skills/lw-ticket/references/privacy.md` to the title and body, then write `{"issue": {"title": "<title>", "body": "<body>", "labels": ["type:feature"]}}` to a temp file and run `python3 scripts/sdlc/check_issue.py --event <file>`. It must print `"ok": true`; otherwise fix the missing sections or flagged categories and re-run. Discussions are written by many people - never carry names, phone numbers, IDs or partner-confidential details across.

5. **Preview** title (`[Feature] ...`), labels (`type:feature` plus `area:<key>` only if the repo is clear, else `status:triage`), the suggested priority (in the body only) and the full body. Ask "Shall I create this issue? (yes / change something)". Act only on an explicit yes.

6. **Create and link back** (after yes):
   1. `gh issue create --repo Medtronic-LABS/leapwell --title '<title>' --body-file <tmpfile> --label type:feature --label <area:... or status:triage>`
   2. `gh project item-add 4 --owner Medtronic-LABS --url <issue-url>`
   3. Comment on the discussion (body in a temp file: "Promoted to <issue-url>"):
      `gh api graphql -F discussionId=<id> -F body=@<comment-file> -f query='mutation($discussionId:ID!,$body:String!){addDiscussionComment(input:{discussionId:$discussionId,body:$body}){comment{url}}}'`
   Delete the temp files.

7. **Report** the issue link, labels, comment link, and the next step (`/lw-route <N>` by a developer).

Never create, comment or label without an explicit yes; never set priority, assignees or project fields; never close or lock the discussion.
