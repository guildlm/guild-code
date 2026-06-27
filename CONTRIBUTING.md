# Contributing to the Code Guild

Thanks for helping sharpen GuildLM's Go specialists! This repo holds **specs and
recipes**, not training code — so most contributions are YAML, prompts, and
evaluation data that stay faithful to the core tools
([forge](https://github.com/guildlm/forge),
[anvil](https://github.com/guildlm/anvil),
[crucible](https://github.com/guildlm/crucible),
[brain](https://github.com/guildlm/brain)).

## Ground rules

- **Schema-faithful.** Every recipe must validate against the real loader:
  forge (`forge/configs/example.yaml`), anvil (`anvil/src/config.py`), crucible
  (`crucible/suites/*.yaml`). Do not introduce fields those loaders don't define.
- **Offline-first.** Recipes and suites must run with no network and no GPU:
  `generate.offline: true` for forge, `llm_judge.offline: true` for crucible.
- **Brain-aligned.** A specialist's id, base model and prompt intent in
  `go/guild.yaml` must match its entry in `brain/configs/guilds.yaml`.

## Validate before opening a PR

```bash
# Every YAML must parse
find . -name '*.yaml' -print0 | xargs -0 -I{} \
  python3 -c "import sys,yaml; yaml.safe_load(open(sys.argv[1]))" {}

# Shell tooling must be syntactically clean
bash -n go/tools/run_tests.sh
shellcheck go/tools/run_tests.sh   # if shellcheck is installed
```

For a deeper check, run a recipe end-to-end against a sibling tool checkout:

```bash
forge run --config go/forge/go_generator.yaml          # offline synthetic data
go/tools/run_tests.sh go_reviewer                      # offline judge
```

## Adding a new specialist

1. Add a system prompt under `go/prompts/<short>.txt`.
2. Add recipes: `go/forge/<id>.yaml`, `go/anvil/<id>.yaml`,
   `go/crucible/<id>.yaml` (with a sample dataset in `go/crucible/data/`).
3. If forge has no matching teacher role, add one to
   `forge/src/core/instruction_gen.py` (see
   [DATASETS.md](./DATASETS.md#adding-the-go_tester-teacher-role)).
4. Register the specialist in `go/guild.yaml` **and** in
   `brain/configs/guilds.yaml` with the same `brain_id`.
5. Update the status table in [README.md](./README.md#specialists).

## Adding a new language to the Code Guild

Mirror the `go/` directory for the new language (`rust/`, `python/`, …) with its
own `guild.yaml`, recipes, prompts and suites. Keep the Code Guild's domain
(`code`) but scope the routing keywords to the language.

## Commit messages

Write clear, imperative subjects (e.g. "Add go_optimizer specialist"). Reference
related issues where relevant.

## License

By contributing, you agree your contributions are licensed under the Apache
License 2.0.
