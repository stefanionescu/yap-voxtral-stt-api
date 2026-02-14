from __future__ import annotations

from src.runtime.gpu_profiles import select_max_num_batched_tokens


def test_select_max_num_batched_tokens_l40s() -> None:
    assert select_max_num_batched_tokens("NVIDIA L40S") == 2048


def test_select_max_num_batched_tokens_l40() -> None:
    assert select_max_num_batched_tokens("NVIDIA L40") == 2048


def test_select_max_num_batched_tokens_rtx_6000() -> None:
    assert select_max_num_batched_tokens("NVIDIA RTX 6000 Ada Generation") == 2048


def test_select_max_num_batched_tokens_a100() -> None:
    assert select_max_num_batched_tokens("NVIDIA A100-SXM4-80GB") == 2048


def test_select_max_num_batched_tokens_h100() -> None:
    assert select_max_num_batched_tokens("NVIDIA H100 80GB HBM3") == 4096


def test_select_max_num_batched_tokens_b200() -> None:
    assert select_max_num_batched_tokens("NVIDIA B200") == 4096


def test_select_max_num_batched_tokens_unknown() -> None:
    assert select_max_num_batched_tokens("Some Unknown GPU") == 2048
