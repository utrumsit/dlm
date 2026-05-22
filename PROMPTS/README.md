# DLM Linux Port — Prompts for Qwen 3 6B

Seven phased prompts to port DLM from macOS-only to cross-platform (Mac + Linux), feed them to a coding agent (e.g. Qwen 3 6B) one at a time.

## Order

1. **phase1.md** — Reader abstraction (pure refactor, no behavior change)
2. **phase2.md** — TOML config + `dlm config` CLI
3. **phase3.md** — `dlm doctor` diagnostic command
4. **phase4.md** — Sioyek reader (Linux + Mac PDF)  ← *needs prerequisite SQL paste*
5. **phase5.md** — Foliate reader (Linux EPUB)  ← *needs prerequisite JSON paste*
6. **phase6.md** — Clipboard-based `ask` + LLM abstraction
7. **phase7.md** — Cross-platform packaging & docs

## Prerequisites (do these yourself before running the prompts)

1. **Pin a working git commit** before starting — easy rollback if the agent goes sideways.
   ```
   cd ~/karl-dev/dlm
   git tag pre-linux-port
   ```

2. **Before phase4.md**, confirm Sioyek's SQLite schema (versions drift):
   ```
   sqlite3 ~/.local/share/sioyek/shared.db ".schema highlights"
   sqlite3 ~/.local/share/sioyek/shared.db ".schema bookmarks"
   ```
   Paste the actual schema into phase4.md where indicated.

3. **Before phase5.md**, confirm Foliate's annotation file layout:
   ```
   foliate /path/to/some.epub  # add a highlight, close
   ls ~/.local/share/com.github.johnfactotum.Foliate/library/
   cat ~/.local/share/com.github.johnfactotum.Foliate/library/<file>.json | head -50
   ```
   Paste a sample into phase5.md.

## How to drive the agent

- **One phase at a time.** Each prompt is self-contained — don't combine them.
- **Commit between phases.** If a phase produces garbage, roll back that one without losing the others.
- **Verify each phase's "Verify" block** before moving on.
- **Phase 4 is the riskiest.** Sioyek's SQLite schema actually drifts between versions. If the prerequisite output differs from the SQL in the prompt, edit the SQL in the prompt before sending.
- **Watch for hallucinated APIs.** A 6B model will sometimes invent flags like `sioyek --json-state`. After phases 4 + 5, manually verify the `subprocess` calls against `sioyek --help` / `foliate --help` on your system.
- **Skip Phase 7 if the agent's prose is rough** — docs are easy to write yourself once the code works.
