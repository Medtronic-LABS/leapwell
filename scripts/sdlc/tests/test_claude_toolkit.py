"""Structure checks for the committed Claude toolkit (.claude/ agents and skills)."""
import json
import re
import subprocess
import unittest
from pathlib import Path

from scripts.sdlc import repos
from scripts.sdlc.check_issue import evaluate
from scripts.sdlc.patterns import PRIVACY_HEADING, REQUIRED_SECTIONS, TYPE_LABELS, find_sensitive

ROOT = Path(__file__).resolve().parents[3]
CLAUDE = ROOT / ".claude"
AGENTS_DIR = CLAUDE / "agents"
SKILLS_DIR = CLAUDE / "skills"
TICKET_DIR = SKILLS_DIR / "lw-ticket"
FORMS_DIR = ROOT / ".github" / "ISSUE_TEMPLATE"
LABELS_FILE = ROOT / ".github" / "labels.yml"
FRAPPE_CHECKLIST = CLAUDE / "references" / "frappe-review-checklist.md"

HOOK_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR"/scripts/sdlc/guard_tool.py'
READ_TOOLS = {"Read", "Grep", "Glob", "Bash"}
AGENTS = {
    "lw-architect": ("opus", READ_TOOLS),
    "lw-implementer": ("sonnet", READ_TOOLS | {"Edit", "Write"}),
    "lw-reviewer": ("opus", READ_TOOLS),
    "lw-qa": ("sonnet", READ_TOOLS | {"Write", "Edit"}),
    "lw-security": ("opus", READ_TOOLS),
    "lw-release": ("sonnet", READ_TOOLS),
    "lw-frappe-db": ("sonnet", READ_TOOLS),
    "lw-devops": ("sonnet", READ_TOOLS),
}
READ_ONLY_AGENTS = {"lw-architect", "lw-reviewer", "lw-security", "lw-release", "lw-frappe-db", "lw-devops"}
WORKFLOW_SKILLS = {"lw-start", "lw-feature", "lw-fix", "lw-pr", "lw-release"}
HUB_SKILLS = {"lw-setup", "lw-route", "lw-promote", "lw-wiki"}
MANUAL_SKILLS = WORKFLOW_SKILLS | HUB_SKILLS
AREA_STATUS_SKILLS = {"lw-frappe-status", "lw-ai-status", "lw-coaching-status"}
AREA_ACTION_SKILLS = {
    "lw-mobile-start", "lw-mobile-fresh-launch", "lw-mobile-e2e", "lw-mobile-release",
    "lw-frappe-setup", "lw-frappe-start", "lw-frappe-stop",
    "lw-ai-start", "lw-ai-stop", "lw-ai-test",
    "lw-coaching-start", "lw-coaching-stop", "lw-coaching-android-build",
}
AREA_SKILLS = AREA_ACTION_SKILLS | AREA_STATUS_SKILLS
ALL_SKILLS = MANUAL_SKILLS | AREA_SKILLS | {"lw-ticket"}
FRAPPE_ENV = ROOT / "env" / "frappe"
MAX_AREA_SKILL_LINES = 80
TICKET_TYPES = ("bug", "feature", "task", "release")
HARD_LIMIT_PHRASES = ("never merge", "never set priority", "prod", "secret")
MAX_TICKET_SKILL_LINES = 220
MAX_WORKFLOW_SKILL_LINES = 80
TRACKER = "Medtronic-LABS/leapwell"
LEGACY_TRACKER = "Medtronic-LABS/uhis_lf_mobile"

REPO_PATH_RE = re.compile(r"\brepos/(?!Medtronic-LABS/)([A-Za-z0-9_.-]+)")  # not REST paths
ORG_SLUG_RE = re.compile(r"\bMedtronic-LABS/([A-Za-z0-9_.-]+?)(?=[#/\s`'\")\].,]|$)")
SKILL_CALL_RE = re.compile(r"/lw-(?:start|fix|feature|pr|release) ([a-z][\w-]*)")
AREA_LABEL_RE = re.compile(r"\barea:([a-z][\w-]*)")


def frontmatter(path):
    """Return ({key: value}, body) for a file that starts with a `---` block."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"{path} does not start with ---")
    end = text.index("\n---\n", 4)
    meta = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith(" "):
            meta[key.strip()] = value.strip()
    return meta, text[end + 5:]


def skill(name):
    return frontmatter(SKILLS_DIR / name / "SKILL.md")


def form_options(name):
    """Dropdown options of an issue form, keyed by field label."""
    text = (FORMS_DIR / f"{name}.yml").read_text(encoding="utf-8")
    options = {}
    for block in re.split(r"^  - type: ", text, flags=re.MULTILINE)[1:]:
        if not block.startswith("dropdown"):
            continue
        label = re.search(r"^      label:\s*(.+?)\s*$", block, re.MULTILINE).group(1)
        options[label] = re.findall(r"^        - (.+?)\s*$", block, re.MULTILINE)
    return options


def toolkit_files():
    return sorted(p for p in CLAUDE.rglob("*") if p.is_file() and p.suffix in {".md", ".json"})


class SettingsTest(unittest.TestCase):
    def test_hooks_only_with_guard_tool(self):
        settings = json.loads((CLAUDE / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(set(settings), {"hooks"})
        self.assertEqual(set(settings["hooks"]), {"PreToolUse"})
        [entry] = settings["hooks"]["PreToolUse"]
        self.assertEqual(entry["matcher"], "Bash|Read|Edit|Write|Grep")
        [hook] = entry["hooks"]
        self.assertEqual(hook, {"type": "command", "command": HOOK_COMMAND, "timeout": 10})


class AgentsTest(unittest.TestCase):
    def test_exact_agent_set(self):
        self.assertEqual({p.stem for p in AGENTS_DIR.glob("*.md")}, set(AGENTS))

    def test_frontmatter(self):
        for name, (model, tools) in AGENTS.items():
            meta, _ = frontmatter(AGENTS_DIR / f"{name}.md")
            self.assertEqual(meta.get("name"), name)
            self.assertTrue(meta.get("description"), name)
            self.assertEqual(meta.get("model"), model, name)
            declared = {t.strip() for t in meta.get("tools", "").split(",")}
            self.assertTrue(tools <= declared, f"{name} tools {declared}")
            if name in READ_ONLY_AGENTS:
                self.assertFalse({"Edit", "Write"} & declared, f"{name} must be read-only")

    def test_hard_limits_stated(self):
        for name in AGENTS:
            _, body = frontmatter(AGENTS_DIR / f"{name}.md")
            lowered = body.lower()
            self.assertIn("## hard limits", lowered, name)
            self.assertIn("never spawn other agents", lowered, name)
            for phrase in HARD_LIMIT_PHRASES:
                self.assertIn(phrase, lowered, f"{name} lacks {phrase!r}")

    def test_agents_are_repo_aware(self):
        for name in AGENTS:
            _, body = frontmatter(AGENTS_DIR / f"{name}.md")
            self.assertTrue("repos.json" in body or "repos/" in body, f"{name} does not use the manifest")

    def test_reviewer_gives_two_verdicts_and_reads_frappe_checklist(self):
        _, body = frontmatter(AGENTS_DIR / "lw-reviewer.md")
        for verdict in ("Spec ✅", "Spec ❌", "Approved", "Changes requested", "Engineering Design Standards"):
            self.assertIn(verdict, body)
        self.assertIn(".claude/references/frappe-review-checklist.md", body)
        self.assertTrue(FRAPPE_CHECKLIST.is_file())
        checklist = FRAPPE_CHECKLIST.read_text(encoding="utf-8")
        for needle in ("@frappe.whitelist()", "allow_guest=True", "ignore_permissions=True",
                       "frappe.db.sql", "patches.txt", "Password"):
            self.assertIn(needle, checklist)


class SkillsTest(unittest.TestCase):
    def test_exact_skill_set(self):
        self.assertEqual({p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")}, ALL_SKILLS)

    def test_frontmatter(self):
        for name in ALL_SKILLS:
            meta, body = skill(name)
            self.assertEqual(meta.get("name"), name)
            self.assertTrue(meta.get("description"), name)
            self.assertTrue(body.strip(), name)

    def test_manual_only(self):
        for name in MANUAL_SKILLS:
            meta, _ = skill(name)
            self.assertEqual(meta.get("disable-model-invocation"), "true", name)

    def test_focused_length(self):
        for name in MANUAL_SKILLS:
            lines = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8").count("\n")
            self.assertLessEqual(lines, MAX_WORKFLOW_SKILL_LINES, name)

    def test_github_writes_need_explicit_yes(self):
        for name in MANUAL_SKILLS - {"lw-setup", "lw-fix", "lw-feature"}:
            _, body = skill(name)
            self.assertIn("yes", body.lower(), name)

    def test_workflow_skills_are_repo_aware(self):
        for name in WORKFLOW_SKILLS:
            meta, body = skill(name)
            self.assertIn("<repo-key>", meta.get("argument-hint", ""), name)
            for needle in ("repos.json", "integration_branch", "repos/<name>"):
                self.assertIn(needle, body, f"{name} lacks {needle}")
        for name in ("lw-fix", "lw-pr", "lw-feature"):
            self.assertIn("verify", skill(name)[1], name)

    def test_start_suggests_route_for_leapwell_numbers(self):
        _, body = skill("lw-start")
        self.assertIn("/lw-route", body)
        self.assertIn("switch -c <branch> origin/<integration_branch>", body)

    def test_pr_links_issue_and_parent(self):
        _, body = skill("lw-pr")
        for needle in ("Closes #<N>", f"Refs {TRACKER}#<M>", "gh pr create --draft", "--base <base>"):
            self.assertIn(needle, body)
        self.assertIn("--title '<type>(<area>): <summary> (#<N>)'", body)
        self.assertNotIn('--title "', body)

    def test_partial_failures_retry_only_the_failed_step(self):
        for name in ("lw-route", "lw-promote"):
            body = skill(name)[1]
            self.assertIn("Partial failure", body, name)
            self.assertIn("never re-create", body.lower(), name)


class AreaSkillsTest(unittest.TestCase):
    def test_action_skills_are_manual_only(self):
        for name in AREA_ACTION_SKILLS:
            meta, _ = skill(name)
            self.assertEqual(meta.get("disable-model-invocation"), "true", name)

    def test_status_skills_are_read_only_and_model_invocable(self):
        for name in AREA_STATUS_SKILLS:
            meta, body = skill(name)
            self.assertNotIn("disable-model-invocation", meta, name)
            self.assertIn("Read-only", meta["description"], name)
            self.assertNotRegex(body, r"docker compose (up|down)|--stop|--start", name)

    def test_focused_length(self):
        for name in AREA_SKILLS:
            lines = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8").count("\n")
            self.assertLessEqual(lines, MAX_AREA_SKILL_LINES, name)

    def test_mobile_skills_use_the_clone_and_env_file_names(self):
        for name in ("lw-mobile-start", "lw-mobile-fresh-launch", "lw-mobile-e2e", "lw-mobile-release"):
            body = skill(name)[1]
            self.assertIn("repos/uhis_lf_mobile", body, name)
            self.assertIn("env.", body, name)
        _, release = skill("lw-mobile-release")
        for needle in ("dev", "training", "playstore", "scripts/release.sh", "libapp.so",
                       "never commits, pushes, merges, tags", "Play Console"):
            self.assertIn(needle, release)
        self.assertEqual(skill("lw-mobile-release")[0].get("argument-hint"), "<dev|training|playstore>")

    def test_frappe_skills_drive_the_env_script(self):
        flags = {"lw-frappe-setup": "frappe_setup.sh`", "lw-frappe-start": "--start",
                 "lw-frappe-stop": "--stop", "lw-frappe-status": "--status"}
        for name, needle in flags.items():
            self.assertIn("env/frappe/frappe_setup.sh", skill(name)[1], name)
            self.assertIn(needle, skill(name)[1], name)
        self.assertIn("--restart", skill("lw-frappe-start")[1])
        for needle in ("repos/frappe_spice_next_core", "repos/leapwell_shukhee_integration", ".env.example"):
            self.assertIn(needle, skill("lw-frappe-setup")[1])

    def test_ai_skills_drive_the_service_repo(self):
        for name in ("lw-ai-start", "lw-ai-stop", "lw-ai-status", "lw-ai-test"):
            self.assertIn("repos/leapfrog-ai-service", skill(name)[1], name)
        self.assertIn("docker compose up -d", skill("lw-ai-start")[1])
        self.assertIn("http://localhost:8095/health", skill("lw-ai-start")[1])
        self.assertIn("env.example", skill("lw-ai-start")[1])
        self.assertIn("pytest -q", skill("lw-ai-test")[1])

    def test_coaching_skills_use_documented_commands(self):
        start = skill("lw-coaching-start")[1]
        for needle in ("repos/spice-coaching", "repos/spice-coaching-dashboard-ui", "docker compose up --build",
                       "uv sync --locked --all-packages --group dev", "npm run dev", "/medtronics-api/ready"):
            self.assertIn(needle, start)
        android = skill("lw-coaching-android-build")[1]
        for needle in ("repos/spice-coaching-android", ":sdk-android:assembleDebug", ":app:assembleDebug",
                       ":sdk-android:test", "publishToMavenLocal", "Never run `./gradlew :sdk-android:publish`"):
            self.assertIn(needle, android)

    def test_area_skills_name_no_secret_env_values(self):
        for name in AREA_SKILLS:
            body = skill(name)[1]
            self.assertNotRegex(body, r"https?://[\w.-]*(labsplatform|amazonaws)", name)
            self.assertNotRegex(body, r"PASSWORD_HASH_KEY=|--dart-define=PASSWORD", name)


class FrappeEnvTest(unittest.TestCase):
    def test_files_present(self):
        for rel in ("docker-compose.yml", "frappe_setup.sh", ".env.example", "README.md",
                    "docker/backend-v16/Dockerfile", "nginx/frappe.conf.template"):
            self.assertTrue((FRAPPE_ENV / rel).is_file(), rel)

    def test_setup_script_syntax(self):
        result = subprocess.run(["bash", "-n", str(FRAPPE_ENV / "frappe_setup.sh")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_runs_without_docker_or_env_file(self):
        result = subprocess.run(["bash", str(FRAPPE_ENV / "frappe_setup.sh"), "--help"],
                                capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(result.returncode, 0, result.stderr)
        for flag in ("--start", "--stop", "--restart", "--status"):
            self.assertIn(flag, result.stdout)

    def test_refuses_to_run_without_env_file(self):
        if (FRAPPE_ENV / ".env").exists():
            self.skipTest("a local .env exists")
        script = (FRAPPE_ENV / "frappe_setup.sh").read_text(encoding="utf-8")
        self.assertIn("cp .env.example .env", script)
        self.assertIn("[[ -f .env ]] || error", script)

    def test_apps_come_from_workspace_clones(self):
        compose = (FRAPPE_ENV / "docker-compose.yml").read_text(encoding="utf-8")
        for name in ("frappe_spice_next_core", "leapwell_shukhee_integration"):
            self.assertIn(f"../../repos/{name}:/workspace-apps/", compose)
        script = (FRAPPE_ENV / "frappe_setup.sh").read_text(encoding="utf-8")
        self.assertNotIn("bench new-app", script)
        for app in ("spice_next_core", "shukhee_integration"):
            self.assertIn(app, script)

    def test_example_env_has_placeholders_only(self):
        text = (FRAPPE_ENV / ".env.example").read_text(encoding="utf-8")
        for key in ("DB_ROOT_PASSWORD", "ADMIN_PASSWORD", "SITE_NAME", "FRAPPE_BRANCH"):
            self.assertRegex(text, rf"(?m)^{key}=")
        self.assertEqual(text.count("change-me-local-only"), 2)
        for name in ("docker-compose.yml", "frappe_setup.sh"):
            self.assertNotRegex((FRAPPE_ENV / name).read_text(encoding="utf-8"),
                                r"Admin@|:-123\b")

    def test_data_dir_is_gitignored(self):
        self.assertIn("/env/frappe/development/", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())


class HubSkillsTest(unittest.TestCase):
    def test_setup_runs_workspace_script(self):
        _, body = skill("lw-setup")
        for needle in ("bash scripts/workspace/setup.sh", "MISSING", "FAIL", "gh auth login"):
            self.assertIn(needle, body)

    def test_route_flow(self):
        _, body = skill("lw-route")
        for needle in (
            f"gh issue view $ARGUMENTS -R {TRACKER}",
            "--jq .id",
            f"gh api -X POST repos/{TRACKER}/issues/$ARGUMENTS/sub_issues -F sub_issue_id=<id>",
            "Is routing complete for this item?",
            "--add-label status:routed --remove-label status:triage",
            "gh project item-add 4 --owner Medtronic-LABS",
            "python3 scripts/sdlc/check_issue.py --scan-only",
            f"Parent: {TRACKER}#<N>",
            "leapfrog-ai-service",
            "private",
        ):
            self.assertIn(needle, body)
        # The routed label is added only after the completeness question.
        self.assertLess(body.index("Is routing complete"), body.index("--add-label status:routed"))

    def test_promote_flow(self):
        _, body = skill("lw-promote")
        for needle in ("gh api graphql", "discussion(number:", "addDiscussionComment",
                       ".claude/skills/lw-ticket/references/feature.md", "python3 scripts/sdlc/check_issue.py",
                       "--label type:feature", "gh project item-add 4 --owner Medtronic-LABS"):
            self.assertIn(needle, body)

    def test_wiki_flow(self):
        _, body = skill("lw-wiki")
        for needle in (f"https://github.com/{TRACKER}.wiki.git", "python3 scripts/sdlc/scan_text.py",
                       "diff", "push origin HEAD:<wiki-branch>", "symbolic-ref --short HEAD",
                       ".superpowers/wiki", "docs/process/"):
            self.assertIn(needle, body)
        self.assertLess(body.index(" diff"), body.index("push origin HEAD"))
        self.assertNotIn("mktemp", body)
        self.assertNotIn("--force ", body)


class TicketSkillTest(unittest.TestCase):
    def setUp(self):
        self.meta, self.body = frontmatter(TICKET_DIR / "SKILL.md")

    def test_chat_safe_frontmatter(self):
        self.assertEqual(set(self.meta), {"name", "description"})
        for trigger in ("bug", "ticket", "issue", "feature request", "task"):
            self.assertIn(trigger, self.meta["description"].lower())

    def test_focused_length(self):
        lines = (TICKET_DIR / "SKILL.md").read_text(encoding="utf-8").count("\n")
        self.assertLessEqual(lines, MAX_TICKET_SKILL_LINES)

    def test_self_contained(self):
        for path in TICKET_DIR.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("../", text, f"{path} reaches outside the skill folder")
        for ref in re.findall(r"references/[\w-]+\.md", self.body):
            self.assertTrue((TICKET_DIR / ref).is_file(), ref)
        for issue_type in TICKET_TYPES:
            self.assertIn(f"references/{issue_type}.md", self.body)
        self.assertIn("references/privacy.md", self.body)

    def test_flow_essentials(self):
        for needle in (
            "gh issue list", "--body-file", "gh project item-add 4 --owner Medtronic-LABS",
            f"gh issue create --repo {TRACKER}", "issue_write", "issues/new?template=",
            f"https://github.com/{TRACKER}/security/advisories/new",
            "AskUserQuestion", "adb devices", "prio:", "env:", "status:triage",
        ):
            self.assertIn(needle, self.body)

    def test_duplicate_search_covers_tracker_and_legacy(self):
        self.assertIn(f"gh issue list --repo {TRACKER} --state open", self.body)
        self.assertIn(f"gh issue list --repo {LEGACY_TRACKER} --state open", self.body)

    def test_area_label_for_every_repo(self):
        for repo in repos.load().repos:
            self.assertIn(f"`area:{repo.key}`", self.body)
            self.assertIn(repo.name, self.body)

    def test_type_labels_are_the_contract(self):
        for label in TYPE_LABELS:
            self.assertIn(label, self.body)
        for legacy in ("`bug`, `enhancement`", "`chore`"):
            self.assertNotIn(legacy, self.body)

    def test_references_carry_contract_headings(self):
        for issue_type in TICKET_TYPES:
            text = (TICKET_DIR / "references" / f"{issue_type}.md").read_text(encoding="utf-8")
            for heading in REQUIRED_SECTIONS[issue_type]:
                self.assertRegex(text, rf"(?m)^### {re.escape(heading)}$", f"{issue_type}: {heading}")

    def test_body_templates_pass_issue_check(self):
        type_label = {issue_type: label for label, issue_type in TYPE_LABELS.items()}
        for issue_type in TICKET_TYPES:
            text = (TICKET_DIR / "references" / f"{issue_type}.md").read_text(encoding="utf-8")
            body = re.search(r"```markdown\n(.*?)```", text, re.DOTALL).group(1)
            result = evaluate(f"[{issue_type}] summary", body, [type_label[issue_type]])
            self.assertTrue(result.ok, f"{issue_type}: {result}")

    def test_privacy_section_template_is_ticked(self):
        for issue_type in TICKET_TYPES:
            if PRIVACY_HEADING not in REQUIRED_SECTIONS[issue_type]:
                continue
            text = (TICKET_DIR / "references" / f"{issue_type}.md").read_text(encoding="utf-8")
            self.assertIn("- [x] This issue contains no patient/member data", text, issue_type)

    def test_references_offer_form_dropdown_options(self):
        for issue_type in TICKET_TYPES:
            text = (TICKET_DIR / "references" / f"{issue_type}.md").read_text(encoding="utf-8")
            for label, options in form_options(issue_type).items():
                for option in options:
                    self.assertIn(option, text, f"{issue_type}/{label}: {option}")

    def test_privacy_reference_covers_categories(self):
        text = (TICKET_DIR / "references" / "privacy.md").read_text(encoding="utf-8").lower()
        for needle in ("phone", "nid", "email", "gps", "token", "password", "logcat", "<member-id>", "screenshot"):
            self.assertIn(needle, text)


class RepoReferencesTest(unittest.TestCase):
    """Every repo key, repo path, org slug and area label in .claude/ must exist."""

    @classmethod
    def setUpClass(cls):
        manifest = repos.load()
        cls.keys = {r.key for r in manifest.repos}
        cls.names = {r.name for r in manifest.repos}
        cls.slugs = cls.names | {manifest.tracker}
        labels = LABELS_FILE.read_text(encoding="utf-8")
        cls.areas = set(re.findall(r"(?m)^- name: area:([\w-]+)\s*$", labels))

    def scan(self, pattern, allowed, what):
        for path in toolkit_files():
            for value in pattern.findall(path.read_text(encoding="utf-8")):
                self.assertIn(value, allowed, f"{path.relative_to(ROOT)}: unknown {what} {value!r}")

    def test_repo_paths(self):
        self.scan(REPO_PATH_RE, self.names, "repos/ path")

    def test_org_slugs(self):
        self.scan(ORG_SLUG_RE, self.slugs, "Medtronic-LABS repo")

    def test_skill_call_repo_keys(self):
        self.scan(SKILL_CALL_RE, self.keys, "repo key")

    def test_area_labels(self):
        self.scan(AREA_LABEL_RE, self.areas, "area label")

    def test_patterns_catch_bad_values(self):
        self.assertEqual(REPO_PATH_RE.findall("repos/not-a-repo and repos/<name>"), ["not-a-repo"])
        self.assertEqual(SKILL_CALL_RE.findall("`/lw-start mobile 12`, `/lw-fix <key> <N>`"), ["mobile"])
        self.assertEqual(ORG_SLUG_RE.findall(f"{TRACKER}#3 and Medtronic-LABS/<name>"), ["leapwell"])


class ToolkitPrivacyTest(unittest.TestCase):
    def test_no_sensitive_values_committed(self):
        for path in toolkit_files():
            found = find_sensitive(path.read_text(encoding="utf-8"))
            self.assertEqual(found, [], f"{path.relative_to(ROOT)}: {found}")


if __name__ == "__main__":
    unittest.main()
