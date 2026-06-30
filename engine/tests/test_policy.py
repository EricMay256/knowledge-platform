"""Policy.__post_init__ ordering + range invariants.

B2 GUARD: the A stage only ever sets flag_at, but B2 sets the full band table,
so the ordering/range guard must be correct now.
"""

from __future__ import annotations

import pytest

from vault_contrib.models import Policy


def test_a_policy_valid():
    Policy(flag_at=0.85)  # flag_at only; other bands None


def test_full_ordered_policy_valid():
    Policy(reject_at=0.97, merge_at=0.93, flag_at=0.85, link_at=0.70)


def test_equal_adjacent_bands_allowed():
    # Ordering is >=, not >, so equal neighbours are legal.
    Policy(reject_at=0.90, merge_at=0.90, flag_at=0.90, link_at=0.90)


def test_out_of_order_raises():
    with pytest.raises(ValueError, match="out of order"):
        Policy(merge_at=0.80, flag_at=0.85)  # merge_at must be >= flag_at


def test_out_of_order_across_gap_raises():
    with pytest.raises(ValueError):
        Policy(reject_at=0.50, flag_at=0.85)


@pytest.mark.parametrize("bad", [-0.01, 1.01, 2.0])
def test_out_of_range_raises(bad):
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        Policy(flag_at=bad)


def test_none_bands_skipped_in_ordering():
    # Only "present" (non-None) bands are compared; gaps don't trip the check.
    Policy(reject_at=0.95, flag_at=0.60)  # merge_at/link_at None -> fine
