
[中文](./docs/README_zh.md)

# SublimeNoteSync

Simple note workflow for Sublime Text with automatic Git sync.  
Local files + background sync + instant exit.

---

## What it does

- Creates notes in a dated folder structure
- Auto-saves on edit (debounced)
- Auto `git pull → add → commit → push`
- Safe quit (`⌘Q`): save + spawn async push + exit immediately
- Works offline (push later)

No UI. No popup. No commands needed once installed.

<img src="./docs/show.gif" width="600">

---

## Directory structure

```
~/Documents/SublimeNotes/-notes/YYYY-MM/note_YYYY-MM-DD_HH-MM-SS.txt
```

`-notes` sorts to the top of the sidebar. On load, any legacy top-level `YYYY-MM` folders are moved under it.

Example:

```
-notes/
  2025-02/
    note_2025-02-18_21-44-11.txt
    note_2025-02-19_10-02-55.txt
```

---

## Installation

### 1) Plugin file

Sublime → `Preferences → Browse Packages…`

Create:

```
Packages/User/notes_sync.py
```

Paste the script from this repo.

---

### 2) Config file

Create:

```
~/.sublime_note_sync.json
```

Content:

```json
{
  "repo_path": "~/Documents/SublimeNotes",
  "auto_create_repo_dir": true,

  "git_remote": "git@github.com:YOUR_NAME/sublime-notes-sync.git",

  "auto_save_delay_ms": 800,
  "git_debounce_ms": 5000,
  "commit_prefix": "auto",

  "git_user": {
    "user.name": "YOUR NAME",
    "user.email": "YOUR@EMAIL"
  }
}
```

---

### 3) Key binding (safe exit)

Sublime → Key Bindings (User)

```json
{ "keys": ["super+q"], "command": "notes_safe_exit" }
```

---

## Usage

### New note

Command Palette:

```
New Note
```

(Optional)

```json
{ "keys": ["super+n"], "command": "new_note" }
```

### Daily flow

- Create note
- Type
- Close Sublime
- Sync happens in background

---

## First-time repo setup

Option A — let plugin init automatically (recommended)

Option B — clone manually:

```bash
git clone git@github.com:YOUR_NAME/sublime-notes-sync.git ~/Documents/SublimeNotes
```

---

## Notes

- Push logs: `.notesync_push.log` in repo
- If network unreachable, push runs next time
- Uses `git pull --rebase --autostash` to avoid conflicts

---

## License

MIT
