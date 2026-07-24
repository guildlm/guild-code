#!/usr/bin/env python3
"""mlx_lm.server, with --adapter-path actually applied.

WHY THIS EXISTS (measured 2026-07-24, mlx_lm 0.31.3): `mlx_lm.server --adapter-path X`
silently serves the BASE model. In ModelProvider.load:

    model_path   = self._model_map.get(model_path, model_path)      # 'default_model' -> real id
    adapter_path = self._adapter_map.get(model_path, adapter_path)  # keyed by the RESOLVED id

`_adapter_map` only ever holds the key 'default_model', but the lookup runs AFTER
`model_path` has been rewritten to the real model id, so it misses and the adapter
falls back to None. The server then answers in the base model's voice with no error,
no warning, and a 200 — a silent-wrong-answer failure, the most dangerous kind for an
A/B: both arms look served, and the "specialist" arm is really the base.

The fix is to register the adapter under the RESOLVED model id as well, so the lookup
hits. Verified against ground truth: the patched server reproduces
`mlx_lm.load(model, adapter_path=...)` output exactly, and differs from the base.

Usage — identical to mlx_lm.server:
    python serve_adapter.py --model <id> --adapter-path <dir> --port 8081
"""
import sys

from mlx_lm import server

_orig_init = server.ModelProvider.__init__


def _init(self, cli_args):
    _orig_init(self, cli_args)
    # The one-line repair: key the adapter by the resolved model id too, which is what
    # load() looks it up by. 'default_model' stays mapped for the startup preload.
    if getattr(cli_args, "adapter_path", None):
        self._adapter_map[cli_args.model] = cli_args.adapter_path


server.ModelProvider.__init__ = _init

if __name__ == "__main__":
    sys.exit(server.main())
