# .ai – skills for coding agents

Each folder in `skills/` is one skill: a `SKILL.md` with `name` / `description` front matter (the Agent Skills
format), read by an agent before the kind of work its description names. They describe **good practice**, not only
what the code does today; each ends with "Where GaugeApp differs today", the known gaps to close when touching that
code. Project facts and hard limits learned on the car stay in [`AGENTS.md`](../AGENTS.md), which wins on conflict.

| Skill | Use it when |
|---|---|
| [`cpp98-embedded`](skills/cpp98-embedded/SKILL.md) | writing or reviewing C++ in `src/` (C++98, two old compilers, code inside the HMI process, SOLID applied to modules and tables) |
| [`bmw-pluginapp-abi`](skills/bmw-pluginapp-abi/SKILL.md) | a new `bmw::` call, handler, HMI state, model, action or event; debugging the framework on the car |
| [`python-asset-generator`](skills/python-asset-generator/SKILL.md) | changing `make_db.py` (layout, texts, ids, screens, pack format) |
| [`host-testing`](skills/host-testing/SKILL.md) | adding tests, or proving a change on the PC before the car |

To use them with Claude Code, link or copy the folders into `.claude/skills/`; other agents can be pointed at this
folder from their own instruction file.
