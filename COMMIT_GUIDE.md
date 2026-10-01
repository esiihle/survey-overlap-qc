# Publishing overlap-qc v0.2.0 with a real commit history

This repo ships with a helper, `build_history_v2.sh`, that turns the v0.2.0
changes into **six coherent feature commits on top of your v0.1.0 commit** —
each a real, self-contained change that builds and passes its tests.

> **Heads-up about your current repo:** on GitHub, everything is committed one
> level too deep — the repo root holds a single `survey-overlap-qc/` folder and
> all the real files sit inside it (which is why the README doesn't show on the
> front page). So we rebuild the history cleanly at the correct root level and
> replace that single mis-nested commit with a force-push. That's safe here:
> it's your repo, one commit, zero forks or stars.

> **On honesty:** every commit will be dated *now*. That's completely normal for
> a weekend portfolio project. Do **not** backdate commits to fake a multi-week
> timeline — a cluster pretending to span months is the real red flag, and it's
> easy to spot. To have the history genuinely span time, keep shipping the
> roadmap for real over the coming weeks.

You need **both** zips: `survey-overlap-qc.zip` (v0.1.0) and
`survey-overlap-qc-v0.2.0.zip` (v0.2.0).

---

## Step 1 — extract v0.1.0 into a fresh folder

Right-click `survey-overlap-qc.zip` -> Extract All (e.g. to your Desktop). Drill
in until you reach the folder that **directly contains `src`, `README.md`, and
`pyproject.toml`** — that exact folder is your repo root. (Don't stop on a
folder that just contains *another* `survey-overlap-qc` folder — that nesting is
what we're fixing.)

## Step 2 — open that folder in VSCode

File -> Open Folder -> select the folder from Step 1.

## Step 3 — open a Git Bash terminal in VSCode

Terminal -> New Terminal, then click the dropdown arrow next to the `+` in the
terminal panel -> choose **Git Bash**. (No Git Bash? Install "Git for Windows",
then reopen VSCode. On Mac/Linux, the default terminal is fine.)

## Step 4 — make the baseline commit

Put your real GitHub-verified email on line 2 so the commits attribute to you
and count on your contribution graph:

```bash
git init
git config user.name  "Sicelwesihle Myeza"
git config user.email "your-github-email@example.com"
git add -A
git commit -m "feat: initial release v0.1.0"
```

## Step 5 — overlay the v0.2.0 files

Extract `survey-overlap-qc-v0.2.0.zip`, drill into its inner folder (again, the
one that directly contains `src/`), select everything (Ctrl+A), copy (Ctrl+C),
then paste into your VSCode folder and choose **"Replace the files in the
destination."** This overwrites the changed files and adds the new ones
(including `build_history_v2.sh`).

## Step 6 — build the six feature commits

Back in the VSCode terminal:

```bash
bash build_history_v2.sh
```

You should see it create six commits and print a 7-line history.

## Step 7 — connect to your repo and push (replacing the nested commit)

```bash
git remote add origin https://github.com/esiihle/survey-overlap-qc.git
git branch -M main
git push -u origin main --force
```

The `--force` swaps out the mis-nested single commit for the clean history. If a
GitHub sign-in window pops up, authorise it. (If `git remote add` says origin
already exists, use `git remote set-url origin https://github.com/esiihle/survey-overlap-qc.git`
instead.)

## Step 8 — clean up and verify

```bash
rm build_history_v2.sh COMMIT_GUIDE.md
```

Refresh the GitHub page — the **README now renders at the root**, files sit at
the top level, and there are **7 commits**.

---

## What the history will look like

```
docs: release v0.2.0
feat: logging and CLI surface for the new capabilities
feat: pairwise matrix and large-set handling in the HTML report
feat: CSV, TSV and Parquet table I/O
feat: IQR heavy-selector rule
feat: pairwise overlap & Jaccard matrix
feat: initial release v0.1.0
```

Each feature commit ships its own tests, so the suite grows commit by commit
(14 -> 20 -> 24 -> 27 -> 30). CI runs on every push.

## Before you make it public — quick checklist

- [ ] `LICENSE`: replace the placeholder name with your full legal name.
- [ ] Confirm your manager's sign-off covers publishing generalised,
      synthetic-data versions with no client data or names.
- [ ] Sanity check: no client data here — the only data is synthetic, from
      `scripts/generate_synthetic_data.py`.
- [ ] Optional: `gitleaks detect` once before the first push.
