# GuildLM

**A guild of small, sharp Go specialists — wrapped in a verification-driven agent loop.**

GuildLM is an experiment with one thesis:

> **capability = model × algorithm**

A 7B model that's *specialized* for a craft and driven by a **compile-and-test agent loop** — grounded by retrieval, guarded by deterministic gates — writes correct, tested Go that a much larger general model, prompted once, does not. We build the small specialists *and* the algorithm that makes them punch up.

Everything here is trained and measured locally on Apple Silicon with MLX. **Total cloud spend: $0.**

---

## The Code Guild

Three Go specialists, each fused into a standalone model with its **own identity** (ask one who it is — it answers GuildLM, not the base it was built on):

| Model | Craft | Headline |
|---|---|---|
| [**go-dev**](https://huggingface.co/guildlm/go-dev) | writes idiomatic, stdlib-first Go | builds whole backends **green on the first try** in the loop |
| [**go-test**](https://huggingface.co/guildlm/go-test) | writes thorough table-driven tests | catches **14/18 injected bugs vs 7/18** for its base — **2×** |
| [**go-review**](https://huggingface.co/guildlm/go-review) | audits for bugs a green build hides | the distinct second opinion in the loop |

They're meant to work **together**: decompose a spec → `go-dev` writes the code → `go-test` writes the tests → `go build / vet / test` → repair → `go-review` audits. That's the [Builder](https://github.com/guildlm/builder).

---

## What we've actually shown (honestly)

We keep a public [research log](https://guildlm.github.io/research/) with every experiment — **wins and losses**:

- **Code base > general model** is the robust win for Go (a code-specialized 7B beats a general one by +3/+4 pass@1).
- **Per-role fine-tuning is mostly *not* the lever** — except for **testing**, where `go-test` genuinely catches 2× the bugs of its base. We don't pretend `go-dev`/`go-review` beat their base solo; their value is the loop.
- **The real levers are the algorithm and the data:** deterministic gates (no third-party reflexes, gofmt/goimports, no trivial tests) + **retrieval grounding**. Two verified examples of a contract the base gets wrong lift a whole backend from 2/3 → **3/3** — and it generalizes across HTTP routing, JSON, and race-free concurrency.

---

## Use them

```bash
# Apple Silicon (MLX)
pip install mlx-lm
python -m mlx_lm generate --model guildlm/go-dev --prompt "Write an idiomatic Go LRU cache." --max-tokens 400

# Ollama (GGUF) — build from the model's Modelfile
ollama run guildlm/go-test "Write httptest tests for a POST /echo JSON endpoint."

# Best: drive the guild with the agent loop
# → github.com/guildlm/builder
```

All models are Apache-2.0 derivatives of [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) (© Alibaba Cloud), fine-tuned, fused, and branded by GuildLM under the same license.

---

- 🛠️ **Agent loop (Builder):** https://github.com/guildlm/builder
- 📓 **Research log:** https://guildlm.github.io/research/
- 💻 **Code & datasets:** https://github.com/guildlm
