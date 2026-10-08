---
name: workspace-mapper
description: This skill should be used to create, scaffold, update, or check the workspace-documentation system for a directory — a root CLAUDE.md map that routes to a CONTEXT.md (what's here + what's being worked on now) and, where needed, a REFERENCES.md (external services, credential locations) in each folder or sub-project. It has three modes — map an existing directory (scan, ask, write, including converting older layouts), scaffold a brand-new project from a description (create real directories plus the docs), and check an existing tree for drift (broken paths, unrouted folders, stale "Now" sections). Trigger phrases include "create a CLAUDE.md", "map this directory", "write a workspace map", "update the CLAUDE.md for this folder", "write a CONTEXT.md", "write a REFERENCES.md", "document the external services for this folder", "set up a new project folder", "scaffold a new client/project workspace", "create the folder structure for X", "start a new workspace using my convention", "check my CLAUDE.md files", "is the map out of date", or "audit the workspace docs".
---

# Workspace Mapper

Three file types let Claude (and people) orient in a project without re-deriving context every session:

| File | Where | Job |
|---|---|---|
| `CLAUDE.md` | Project root (and any nested project root) | The map: what the project is, where to find what, which `CONTEXT.md` to read before working anywhere, what to ignore |
| `CONTEXT.md` | Each folder or sub-project that needs explaining | **What's here** (stable: contents, purpose, what not to assume) + **Now** (dated: what's being worked on) |
| `REFERENCES.md` | Only where something external exists | External services, APIs, credential *locations*, key docs |

One escape hatch: when a folder's **Now** grows into a full phase tracker, it moves to a `STATUS.md` beside the `CONTEXT.md`, and **Now** keeps a one-line pointer to it. This is rare — most projects never need one.

## Why it's shaped this way

This follows how Claude Code loads files:

- `CLAUDE.md` in the launch folder **and every parent folder** loads at session start. A `CLAUDE.md` in a subfolder loads on demand when Claude reads a file there.
- `CONTEXT.md`, `REFERENCES.md` and `STATUS.md` are plain files. Claude reads them **only when something points to them**.

So the root `CLAUDE.md` does the routing: it lists each folder's `CONTEXT.md` and carries a standing rule to read it before working in that folder. Because parents load at launch, the rule still applies when a session starts deep inside a sub-folder. A `CONTEXT.md` that no map points to will never be read — that's the main thing Check mode looks for.

The other rule is separating stable from changing content. **What's here** stays true for months; **Now** goes stale in days. Keeping them in separate sections, with a date on **Now**, means a stale status never makes the stable part look untrustworthy, and Claude can tell how old the status is.

## Which folders get which file

- **Project root** → always `CLAUDE.md`. Add a root `REFERENCES.md` for shared services (hosting, domain, analytics) used across folders. Add a root `CONTEXT.md` only if there's active work that doesn't belong to any one folder — `CLAUDE.md` never holds "Now".
- **Top-level folders and sub-projects** → `CONTEXT.md`, unless the name and the map's one-line description already say everything (`assets/`, `scripts/`, `exports/`).
- **Folders inside those** → describe them in the parent `CONTEXT.md`'s **What's here** table. Give one its own `CONTEXT.md` only when it's a sub-project with its own work going on, and route to it from the parent's table.
- **Nested project roots** (their own git repo, or a folder sessions get launched in directly) → their own `CLAUDE.md`, with their own `CONTEXT.md`/`REFERENCES.md` system beneath. The parent map routes to that `CLAUDE.md`.
- **`REFERENCES.md`** → only when the folder uses external services, has `.env`/credential files, depends on an external knowledge base, or has key docs worth linking. An empty one is just another file to go stale.
- **Small flat folders** with a handful of files → nothing. The parent describes them.

---

## File formats

### CLAUDE.md (project root)

```markdown
# [Project Name] — [One-line purpose]

## What this is

[2–3 sentences: what the project is for, who uses it, how it fits with anything around it.
Include facts a newcomer can't infer from folder names — e.g. "Acme is the owner's own
company, not a client", or "this replaced the old `site-v1/` folder".]

## Before you work in a folder

Read that folder's `CONTEXT.md` first (and its `REFERENCES.md` if it has one). It says what
the folder holds and what's being worked on now. Don't infer current status from this file.

## Folder structure

\`\`\`
project/
├── CLAUDE.md              ← This map
├── REFERENCES.md          ← Shared services: hosting, domain, analytics
├── website/               ← Marketing site (Astro) — see website/CONTEXT.md
├── booking-bot/           ← WhatsApp booking assistant — see booking-bot/CONTEXT.md
├── brand/                 ← Logos, fonts, colours — see brand/CONTEXT.md
└── archive/               ← Retired work (ignore)
\`\`\`

## Where to find what

| Want to... | Go to | Read first |
|---|---|---|
| [Common task] | [`folder/`](folder/) | [`folder/CONTEXT.md`](folder/CONTEXT.md) |

## Important notes
[Optional. Cross-cutting gotchas: live-deploy warnings, duplicate copies, naming traps.]

## Ignore
[Folders or files Claude should not read or act on, one-clause reason each.]
```

The "Before you work in a folder" section is the routing mechanism — never drop it. Every folder that has a `CONTEXT.md` must appear in the structure tree or the "Where to find what" table.

### CONTEXT.md (folder or sub-project)

```markdown
# [Folder name] — [One-line purpose]

## What's here

[1–2 short paragraphs: what this folder is for, how it relates to its siblings, and anything
a reader would wrongly assume — e.g. "the deployed bot runs from ../booking-bot/, not from here".]

| Path | What it is |
|---|---|
| `src/` | [one line] |
| `sub-project/` | [one line] — read `sub-project/CONTEXT.md` |

## Now

**Updated:** YYYY-MM-DD

- **Working on:** [current task]
- **Next:** [what comes after]
- **Open:** [blockers, undecided questions]
```

Rules for **Now**:
- Update the date every time the section changes. A dated stale status is useful; an undated one is misleading.
- If nothing is in progress, say so: `Nothing active.` with the date. That tells Claude the folder is quiet, which is information too.
- Keep it short. When it grows past ~20–30 lines or turns into phases and checklists, move it to `STATUS.md` (same format, with history) and leave `See STATUS.md.` in **Now**.

### REFERENCES.md

```markdown
# [Folder Name] — References

External systems, credential locations, and key documents for [folder purpose].

## External services

| Service | Used by | Purpose |
|---|---|---|
| [Service] | [script or subfolder] | [what it does] |

## Credentials

Never commit these. Values live only in the files below. This doc records where they are and which keys they hold.

| File | Keys |
|---|---|
| `path/.env` | `KEY_NAME`, `OTHER_KEY` |

[Setup pointer if non-obvious — e.g. "Copy from `.env.example`".]

## Key docs

| Doc | Purpose |
|---|---|
| [README.md](README.md) | [one line] |

## External knowledge base (if applicable)
[Path and access method for an Obsidian vault, wiki, or other source of truth.]
```

Never write secret **values** into any of these files — only locations and key names.

A root `REFERENCES.md` in a project whose folders have their own should end with a short "Folder references" table pointing to each.

---

## Scanner

```bash
python3 scripts/scan_directory.py /path/to/project --depth 2          # tree with doc markers
python3 scripts/scan_directory.py /path/to/project --depth 3 --check  # tree + drift report
```

(`scripts/scan_directory.py` is relative to this skill's directory.)

Each directory in the tree is annotated with the doc files it has, e.g. `website/  [CONTEXT.md, REFERENCES.md]`. A git repo is marked `(repo)`. No bracket means undocumented.

`--check` adds a drift report:
- **Broken paths** — paths named in a doc (tree entries, backticked paths, markdown links) that don't exist on disk.
- **Unrouted** — a folder with a `CONTEXT.md` that its nearest map or parent `CONTEXT.md` never mentions, so Claude will never be told to read it.
- **Stale Now** — a **Now** section (or `STATUS.md`) whose date is older than `--stale-days` (default 30), or that has no date.
- **Older layout** — a sub-folder `CLAUDE.md` in a folder that isn't a repo, which this system would normally make a `CONTEXT.md`. A candidate for Map/Update, not necessarily wrong.

The check is a heuristic. Read each finding before acting on it: some "broken paths" are commands or placeholders in backticks.

---

## Three modes

Choose the mode from what the user wants and what's on disk:

- **Map/Update** — the directory exists. Scan it, ask about anything unclear, then write or rewrite the docs to match reality. This includes converting an older layout.
- **Scaffold** — nothing exists yet, or a new sub-project is being added to a mapped project. Gather the spec, confirm it, then create the directories and docs.
- **Check** — the user wants to know whether the docs are still accurate. Run `--check`, report what's wrong, and offer fixes. Don't write anything until they agree.

All three produce the same formats and follow the same placement rules.

### Map/Update workflow

1. **Scan.** Run the scanner with `--check` (use `--depth 3` for large trees). This shows the structure, which docs exist, and where they've already drifted.
2. **Read what's there.** Before proposing anything, read the existing docs at the levels you'll touch. Gotchas in `Important notes`, or "what not to assume" lines, often took real investigation to learn — carry them over.
3. **Ask** in a single message, skipping anything the scan already answers:
   1. Project name and purpose, in one sentence.
   2. What each unclear folder is for, listed together.
   3. The most common tasks people come here to do, and where each one lives.
   4. What's being worked on now, folder by folder. These answers fill each **Now** section. Use `Nothing active.` where that's true.
   5. Any external services or credential files you couldn't see.
   6. Anything Claude should ignore.
4. **Draft and confirm.** Show the root `CLAUDE.md` and each `CONTEXT.md`/`REFERENCES.md` you'd write or change. Wait for corrections.
5. **Write.** Only overwrite existing files once the user has confirmed.
6. **Converting an older layout.** If the tree uses sub-folder `CLAUDE.md` files as maps, or keeps a short `STATUS.md`, propose a conversion folder by folder rather than all at once. A sub-folder `CLAUDE.md` in a folder that isn't a project root becomes a `CONTEXT.md`, and its map content moves into **What's here**. A short `STATUS.md` folds into **Now**. Long trackers stay in `STATUS.md` with a pointer. Then update the root map so it routes to each new `CONTEXT.md`.
7. **Finish with Check.** Re-run `--check` and confirm it reports no broken paths and no unrouted folders. Offer to handle the next undocumented folder, one at a time.

### Scaffold workflow

1. **Gather the spec** in a single message:
   1. The name, a one-line purpose, and where it goes. If the parent already has a `CLAUDE.md`, that parent's map will need updating afterwards.
   2. The folder structure. Either the user names the folders, or you propose a structure from their description. Keep it shallow and don't invent folders that aren't needed yet.
   3. For each folder, whether it needs a `CONTEXT.md`, whether it has external services that call for a `REFERENCES.md`, and what's being worked on first, which goes in **Now**.
   4. Any sub-projects that are already known: scaffold them now as a folder plus `CONTEXT.md`, or leave them for later.
2. **Confirm the plan.** Show the directory tree and which docs each level gets, before creating anything.
3. **Create** top-down: the root `CLAUDE.md` first, then each folder's docs. That way every routing line points at a file that exists.
4. **Update the parent.** If this was scaffolded under an existing project, add it to the parent's structure tree and "Where to find what" table. If the parent has a "Folder references" table, add a row there as well. A new folder the parent map doesn't mention will never get read.
5. **Run Check** on the new tree.

### Check workflow

1. Run the scanner with `--check`.
2. Group the findings: broken paths, unrouted folders, stale or undated **Now** sections, older-layout candidates. For each one, say what it means in practice, e.g. "`booking-bot/CONTEXT.md` exists but nothing tells Claude to read it".
3. Propose a specific fix for each finding: edit the path, add a routing row, ask the user what's current to refresh **Now**, or convert the file. Apply the fixes only after the user approves them.

---

## Notes

- The `← description` annotations in the root structure tree are what make the map useful. Never skip them for top-level entries.
- "Where to find what" is the most-used part of `CLAUDE.md`. Accurate beats complete.
- Folders named `Random`, `Archive`, `Old`, `tmp`, `Bin` or similar are candidates for `Ignore`. Raise them with the user rather than assuming.
- Re-check the placement rules before adding a file. Every unwarranted `CONTEXT.md` or `REFERENCES.md` is one more thing to keep current.
- `CLAUDE.md` never tracks status. If you're about to write "currently working on" in a map, it belongs in a **Now** section instead.
