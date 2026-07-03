Save a summary of this session to the Obsidian vault.

## What to do

**Step 1 — Discover and read the current vault notes.**

Use `mcp__obsidian__list_directory` on `C:\Users\Ryan Hanna\Documents\Brain 2.0` to get the current list of notes. Skip the `Sessions/` folder. Read every `.md` file you find using `mcp__obsidian__read_file` with the full path `C:\Users\Ryan Hanna\Documents\Brain 2.0\<note name>`.

This way the skill always works with whatever notes exist — no hardcoded list to maintain.

**Step 2 — Write a session note** at `C:\Users\Ryan Hanna\Documents\Brain 2.0\Sessions\<YYYY-MM-DD>.md`.

If a note for today already exists, read it first and append to it rather than overwriting.

The session note format:
```
Part of [[Daily Sessions]].

## What we worked on
<1-3 bullet points — the actual tasks or topics, not vague summaries>

## Key decisions
<bullet points — only include if a real decision was made. Skip this section if nothing was decided.>

## Important facts learned
<bullet points — things discovered about the codebase, tools, or project that weren't known before. Skip if none.>

## What's next
<1-3 bullet points — concrete next steps, if clear>
```

Keep it tight. No padding. If a section has nothing real to say, omit it entirely.

**Step 3 — Update existing notes** where this session added new information.

Only update a note if something genuinely changed or was decided that affects it. Do not rewrite notes that are already accurate. For each update, make a targeted edit — add a line or bullet, update a status, correct something wrong. Do not rewrite the whole note.

Examples of when to update:
- A PR merged → update `Noah's PRs.md` status
- A new decision was made about the frontend → add it to `Frontend.md`
- We fixed a known issue → remove or update it in the relevant note
- A new file or module was created → add it to `Local Deal Finder.md` codebase map

**Step 4 — Report back** what you wrote and what you updated, in one short paragraph. No need to repeat the full content.
