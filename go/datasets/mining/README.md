# GitHub Go mining pipeline

The **real-data recipe** for the GuildLM Go specialists. Earlier specialists were
trained on a few hundred *synthetic* SFT examples and plateaued (complex
multi-file maintenance stuck at 0/8 for both 7B and 14B). That was never the real
recipe — we had never actually trained on **real, large-scale Go**. This pipeline
fixes that, at $0 / free-tier only (see `never-spend-money`).

It turns thousands of high-quality, permissively-licensed GitHub Go repositories
into two training signals:

1. **DAPT corpus** (`go_dapt_mined.jsonl`) — raw idiomatic Go for one LoRA
   *continued-pretraining* pass that deepens the base's Go knowledge/idioms/
   architecture. This is the untapped **knowledge** lever (on top of the existing
   stdlib corpus in `../pretrain/`).

2. **Git-history task data** — the **gold mine**. Real senior-Go-dev work mined
   from commit history, framed as exactly the user's tasks:
   - `mined_dev.jsonl` — feature/refactor/perf commits → *"apply this change"*
     before→after edit pairs (go-dev).
   - `mined_bugfix.jsonl` — bug-fix commits → buggy→fixed pairs (bug-solving).

3. **PR review data** (`mined_review.jsonl`) — real human code-review feedback
   mined from PR inline comments (code diff hunk → reviewer's comment), the
   training signal for **go-review**.

Both feed the next steps: **DAPT → role-SFT → the agent loop** (the Builder:
retrieval + file-at-a-time edit + verify/repair), measured on `project_bench.py`.

## Stages

| # | Script | Input | Output |
|---|--------|-------|--------|
| 1 | `select_repos.py` | GitHub search API (`gh`) | `repos.jsonl` (repo manifest) |
| 2 | `clone_repos.py` | `repos.jsonl` | `repos/` (bounded-depth clones, gitignored) |
| 3 | `build_dapt_corpus.py` | `repos/` | `go_dapt_mined.jsonl` ({text,source}) |
| 4 | `mine_git_history.py` | `repos/` | `mined_dev.jsonl`, `mined_bugfix.jsonl`, `mined_commits.jsonl` |
| 5 | `mine_pr_reviews.py` | GitHub API (`gh`) | `mined_review.jsonl` |

### 1. `select_repos.py`
Queries the GitHub search API, **bucketed by star ranges** to beat the 1000-
results-per-query cap, so the union spans thousands of repos. Filters:
permissive license only (MIT/Apache-2.0/BSD/ISC/MPL/Unlicense), not archived/
fork, sane size, and drops obvious non-code repos (awesome-lists, books,
tutorials) by name+topic. Sorted by stars.

### 2. `clone_repos.py`
Parallel, **bounded-depth** (`--depth`, default 400) clones — one pass yields both
the HEAD working tree (for DAPT) and recent history (for mining). Resumable
(skips existing clones), disk-aware (stops below `--min-free-gb`), size-aware
(`--max-size-kb` skips mega-repos like kubernetes for small runs).

### 3. `build_dapt_corpus.py`
Walks the clones, skips vendor/testdata/generated files
(`// Code generated ... DO NOT EDIT`, `*.pb.go`, `zz_generated*`, …), dedups by
content hash (optionally vs the stdlib corpus with `--merge-stdlib`), caps
files-per-repo so no single repo dominates. Same `{text,source}` schema as
`../pretrain/go_corpus.jsonl`, so `anvil mode:pretrain` consumes either/both.

### 4. `mine_git_history.py`
Two passes: a cheap `git log --name-status` to list+classify+filter commits, then
`git show sha~1:path` / `git show sha:path` to fetch before/after for kept
commits. Classifies by message (bugfix > perf > feature > refactor), skips junk
subjects (merge/bump/deps/typo/release/version), keeps only real `.go`
modifications within size bounds. Emits chat `{"messages":[...]}` examples in the
same schema as the existing SFT corpora.

### 5. `mine_pr_reviews.py`
Reads the GitHub API (not the local clone — review comments live on PRs). For
each repo, fetches inline PR review comments; each carries a `diff_hunk` (the
code the reviewer saw), so it pairs (Go diff hunk → reviewer comment) into
go-review examples. Drops bots, thread replies, non-`.go` paths, and trivial
chatter (LGTM/nit/thanks/…). Emits `mined_review.jsonl` with the go-review
system prompt.

## Quick start

```bash
# tiny validation run (10 small repos, ~1 min)
./run_mining.sh smoke

# real run — thousands of repos (takes a while; resumable)
MIN_STARS=150 ./run_mining.sh
```

Or run stages individually (see each script's `--help`).

## Outputs & git

Cloned repos (`repos/`) and the large generated corpora (`go_dapt_mined.jsonl`,
`mined_*.jsonl`, `repos*.jsonl`) are **gitignored** — they're regenerated on
demand and far too big to commit. The scripts, this README, and the small
`*.sample.jsonl` previews **are** tracked.

## Next steps after a full run
1. DAPT: `anvil mode:pretrain` on `go_dapt_mined.jsonl` (+ stdlib corpus) to
   deepen the 7B base.
2. Role-SFT the deepened base: go-dev on `mined_dev.jsonl` + `mined_bugfix.jsonl`,
   go-review on `mined_review.jsonl` (+ existing role splits).
3. Run the Builder agent loop and measure on `builder/project_bench.py`.
4. Stay 7B → 14–15B max — the recipe is the lever, not size.
