# workspace-mapper

A Claude Code plugin for keeping a **map that Claude reads first**. Every session starts with no memory of
your project. This plugin writes and maintains the few files that tell Claude what's where, what each folder
is for, and what's being worked on right now, so it stops guessing.

## Install

In Claude Code:

```
/plugin marketplace add Nel-Etienne-Nel/workspace-mapper
/plugin install workspace-mapper@workspace-mapper
```

Then run it with `/workspace-mapper:workspace-mapper`, or just ask Claude to "map this directory",
"set up a new project folder", "check my CLAUDE.md files" and so on.

## The files

| File | Where | Job |
|---|---|---|
| `CLAUDE.md` | Project root | The map: what the project is, where to find what, and a standing rule to read a folder's `CONTEXT.md` before working in it |
| `CONTEXT.md` | Each folder that needs explaining | **What's here** (stable) + **Now** (dated: what's being worked on) |
| `REFERENCES.md` | Only where something external exists | External services, credential *locations*, key docs |

When a **Now** section grows into a full tracker it moves to a `STATUS.md` beside it. Most projects never need one.

```
project/
├── CLAUDE.md              ← The map, loaded at launch
├── REFERENCES.md          ← Shared services
├── website/
│   └── CONTEXT.md         ← What's here + Now
├── booking-bot/
│   ├── CONTEXT.md
│   └── REFERENCES.md      ← Its API keys live in .env (location only, never values)
└── archive/               ← Listed under Ignore in the map
```

## Why it's shaped this way

Claude Code loads `CLAUDE.md` from the launch folder and every parent folder at startup; a `CLAUDE.md` deeper
down only loads when Claude happens to open a file there. `CONTEXT.md` and `REFERENCES.md` are plain files that
Claude reads only when something points to them. So one root map does the routing, and every folder's
`CONTEXT.md` is listed in it. A `CONTEXT.md` nothing points to is never read.

Stable and changing content are kept apart: **What's here** stays true for months, **Now** goes stale in days
and always carries a date, so an old status never makes the rest of the file look untrustworthy.

## What it does

| Mode | What happens |
|---|---|
| Map/Update | Scans an existing folder, asks about anything unclear, writes or rewrites the docs. Converts older layouts (sub-folder `CLAUDE.md` maps) to `CONTEXT.md` |
| Scaffold | Creates a new project or sub-project from a description: real folders plus the docs, then adds it to the parent map |
| Check | Reports drift: paths the docs name that no longer exist, `CONTEXT.md` files no map routes to, stale or undated **Now** sections |

The scanner also runs on its own:

```
python3 skills/workspace-mapper/scripts/scan_directory.py /path/to/project --depth 3 --check
```

The full rules are in [`skills/workspace-mapper/SKILL.md`](skills/workspace-mapper/SKILL.md).

## Licence

MIT.
