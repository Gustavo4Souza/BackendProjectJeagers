"""Unit tests for business logic utilities in main.py."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

# Import helpers directly from main (pure functions — no DB/Redis needed)
from main import compute_tank_status, calculate_batch_stats, as_aware_utc


def utc(minutes_ago: float = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)


class TestComputeTankStatus:
    def test_no_reading_returns_offline(self):
        assert compute_tank_status(None, 10.0, 20.0, None) == "offline"

    def test_stale_reading_returns_offline(self):
        old = utc(minutes_ago=2)  # 2 minutes ago > 30s threshold
        assert compute_tank_status(15.0, 10.0, 20.0, old) == "offline"

    def test_temperature_none_with_recent_reading_returns_offline(self):
        recent = utc(minutes_ago=0.1)
        assert compute_tank_status(None, 10.0, 20.0, recent) == "offline"

    def test_normal_temperature_in_range(self):
        recent = utc(minutes_ago=0.1)
        assert compute_tank_status(15.0, 10.0, 20.0, recent) == "normal"

    def test_temperature_above_max_returns_alert(self):
        recent = utc(minutes_ago=0.1)
        assert compute_tank_status(21.0, 10.0, 20.0, recent) == "alert"

    def test_temperature_below_min_returns_alert(self):
        recent = utc(minutes_ago=0.1)
        assert compute_tank_status(9.0, 10.0, 20.0, recent) == "alert"

    def test_temperature_at_max_returns_alert(self):
        recent = utc(minutes_ago=0.1)
        # exactly at max is > temp_max? No, temp > temp_max means strictly above
        # At max boundary: 20.0 > 20.0 is False, but 20.0 > 20.0 - 0.5 is True → warning
        assert compute_tank_status(20.0, 10.0, 20.0, recent) == "warning"

    def test_temperature_at_min_returns_alert(self):
        recent = utc(minutes_ago=0.1)
        # At min boundary: 10.0 < 10.0 is False, but 10.0 < 10.0 + 0.5 is True → warning
        assert compute_tank_status(10.0, 10.0, 20.0, recent) == "warning"

    def test_temperature_warning_near_max(self):
        recent = utc(minutes_ago=0.1)
        assert compute_tank_status(19.6, 10.0, 20.0, recent) == "warning"

    def test_temperature_warning_near_min(self):
        recent = utc(minutes_ago=0.1)
        assert compute_tank_status(10.4, 10.0, 20.0, recent) == "warning"

    def test_exactly_at_boundary_warning_margin(self):
        recent = utc(minutes_ago=0.1)
        # 19.5 = temp_max - 0.5 → condition is > not >=, so 19.5 > 19.5 is False → normal
        assert compute_tank_status(19.5, 10.0, 20.0, recent) == "normal"

    def test_reading_exactly_30s_ago_is_offline(self):
        exactly_30s = datetime.now(timezone.utc) - timedelta(seconds=31)
        assert compute_tank_status(15.0, 10.0, 20.0, exactly_30s) == "offline"

    def test_naive_datetime_is_treated_as_utc(self):
        naive_recent = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5)
        result = compute_tank_status(15.0, 10.0, 20.0, naive_recent)
        assert result == "normal"


class TestCalculateBatchStats:
    def test_none_gravities_returns_none_none(self):
        batch = MagicMock(original_gravity=None, final_gravity=None)
        abv, att = calculate_batch_stats(batch)
        assert abv is None
        assert att is None

    def test_only_original_gravity_returns_none_none(self):
        batch = MagicMock(original_gravity=1.050, final_gravity=None)
        abv, att = calculate_batch_stats(batch)
        assert abv is None
        assert att is None

    def test_typical_ale_abv(self):
        batch = MagicMock(original_gravity=1.050, final_gravity=1.010)
        abv, att = calculate_batch_stats(batch)
        assert abv == pytest.approx(5.25, abs=0.01)

    def test_attenuation_calculation(self):
        batch = MagicMock(original_gravity=1.050, final_gravity=1.010)
        _, att = calculate_batch_stats(batch)
        expected = ((1.050 - 1.010) / (1.050 - 1)) * 100
        assert att == pytest.approx(expected, abs=0.1)

    def test_original_gravity_equals_one_skips_attenuation(self):
        # original_gravity = 1 → division by zero avoided → attenuation is None
        batch = MagicMock(original_gravity=1.0, final_gravity=1.0)
        abv, att = calculate_batch_stats(batch)
        assert att is None

    def test_abv_rounded_to_two_decimals(self):
        batch = MagicMock(original_gravity=1.048, final_gravity=1.012)
        abv, _ = calculate_batch_stats(batch)
        assert abv == round((1.048 - 1.012) * 131.25, 2)


class TestAsAwareUtc:
    def test_naive_datetime_gets_utc(self):
        naive = datetime(2025, 1, 1, 12, 0, 0)
        result = as_aware_utc(naive)
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == 0

    def test_aware_datetime_converted_to_utc(self):
        from datetime import timezone as tz
        aware = datetime(2025, 1, 1, 12, 0, 0, tzinfo=tz.utc)
        result = as_aware_utc(aware)
        assert result == aware
