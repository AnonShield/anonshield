"""Compatibility shims for third-party OCR libs on newer transformers versions.

`find_pruneable_heads_and_indices` was removed in transformers v5 but is still
imported by surya-ocr 0.17 (see its open issue #492). We restore it as a no-op
implementation so surya can be used alongside transformers v5+ engines
(paddle_vl, lighton_ocr, glm_ocr) without a project-wide downgrade.
"""
from __future__ import annotations

try:
    import transformers.pytorch_utils as _pu
except Exception:
    _pu = None

if _pu is not None and not hasattr(_pu, "find_pruneable_heads_and_indices"):
    import torch

    def find_pruneable_heads_and_indices(heads, n_heads, head_size, already_pruned_heads):
        mask = torch.ones(n_heads, head_size)
        heads = set(heads) - already_pruned_heads
        for head in heads:
            head = head - sum(1 for h in already_pruned_heads if h < head)
            mask[head] = 0
        mask = mask.view(-1).contiguous().eq(1)
        index = torch.arange(len(mask))[mask].long()
        return heads, index

    _pu.find_pruneable_heads_and_indices = find_pruneable_heads_and_indices
