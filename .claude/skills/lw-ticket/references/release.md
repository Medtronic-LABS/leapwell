# Release - questions and body

Matches the GitHub form `release.yml` in Medtronic-LABS/leapwell (template `release`, type label `type:release`, title prefix `[Release] `).
For maintainers tracking a release of one repo. If the user is not a maintainer, suggest they ask one.

| # | Heading (field id) | Ask | Notes |
|---|---|---|---|
| 1 | (title + label) | "Which part are you releasing?" | Mobile app / Frappe core / Teleconsult integration / AI Scribe service / Micro-coaching backend, Android or dashboard. Add its `area:<key>` label (see SKILL.md table). |
| 2 | Version (`version`) | "Which version is this release? (e.g. 1.2.0+16 for the app)" | The repo's own version after the bump PR (app: `pubspec.yaml`, format `x.y.z+build`). Title: `[Release] <repo key> <version>`, e.g. `[Release] mobile 1.2.0+16`. |

The checklist is fixed; do not ask about it. Boxes start unticked - humans tick them as each step is done.
No priority suggestion and no `status:triage`.

## Body template (headings exact)

```markdown
### Version

1.2.0+16

### Release checklist

- [ ] CI green on the integration branch
- [ ] Version bumped
- [ ] Training build verified on a device
- [ ] Release notes written
- [ ] Prod build made from the tagged commit and checksum recorded
```

For a backend or dashboard release, "Training build verified on a device" means verified on the training environment.
