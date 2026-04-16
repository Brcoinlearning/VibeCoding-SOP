# Installing Superpowers for Codex

Enable the skills in this single-repository build via Codex native skill discovery.

## Prerequisites

- Git

## Installation

1. **Clone your single-repository build of this project:**
   ```bash
   git clone https://github.com/Brcoinlearning/VibeCoding-SOP.git ~/.codex/superpowers
   ```

2. **Create the skills symlink:**
   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/superpowers/skills ~/.agents/skills/superpowers
   ```

   **Windows (PowerShell):**
   ```powershell
   New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
   cmd /c mklink /J "$env:USERPROFILE\.agents\skills\superpowers" "$env:USERPROFILE\.codex\superpowers\skills"
   ```

3. **Restart Codex** (quit and relaunch the CLI) to discover the skills.

## Migrating from old bootstrap

If you installed an older nested or upstream-only layout before native skill discovery, you need to:

1. **Update the repo:**
   ```bash
   cd ~/.codex/superpowers && git pull
   ```

2. **Create the skills symlink** (step 2 above) — this is the new discovery mechanism.

3. **Remove the old bootstrap block** from `~/.codex/AGENTS.md` — any block referencing `superpowers-codex bootstrap` is no longer needed.

4. **Restart Codex.**

## Verify

```bash
ls -la ~/.agents/skills/superpowers
```

You should see a symlink (or junction on Windows) pointing to the root `skills/` directory of this repository.

## Updating

```bash
cd ~/.codex/superpowers && git pull
```

Skills update instantly through the symlink as long as the repository root stays at `~/.codex/superpowers`.

## Uninstalling

```bash
rm ~/.agents/skills/superpowers
```

Optionally delete the clone: `rm -rf ~/.codex/superpowers`.

## Notes for This Customized Build

- The active skills root is the repository root `skills/` directory.
- Do not point Codex at `superpowers/skills/` inside the repository. That path is only a migration-period reference source.
