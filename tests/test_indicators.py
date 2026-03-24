"""Unit tests for indicator signal logic and env-var helpers.

Run from the project root:
    python -m pytest tests/ -v
or
    .venv/Scripts/python.exe -m pytest tests/ -v
"""

import os
import sys
import json
import unittest

# Allow imports from src/ without install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# ── Test helpers defined locally so we don't import constant_vars (which
#    reads env vars at module level and requires dotenv to be loaded first) ──
def _bool_env(key, default=False):
    return os.getenv(key, str(default)).strip().lower() in ('true', '1', 'yes')

def _float_env(key, default=0.0):
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default

def _int_env(key, default=0):
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default

def _list_env(key, default=None):
    raw = os.getenv(key, '')
    if not raw:
        return default or []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default or []


# ── Import only the pure functions (no network/file I/O at import time) ──
from indicator_response_generator import _signal_to_int, _composite_score


# ─────────────────────────────────────────────────────────────────────────────
# 1. _signal_to_int
# ─────────────────────────────────────────────────────────────────────────────

class TestSignalToInt(unittest.TestCase):

    def test_buy_returns_1(self):
        self.assertEqual(_signal_to_int('buy'), 1)

    def test_sell_returns_minus1(self):
        self.assertEqual(_signal_to_int('sell'), -1)

    def test_hold_returns_0(self):
        self.assertEqual(_signal_to_int('hold'), 0)

    def test_unknown_returns_0(self):
        self.assertEqual(_signal_to_int(''), 0)
        self.assertEqual(_signal_to_int(None), 0)
        self.assertEqual(_signal_to_int('BUY'), 0)   # case-sensitive


# ─────────────────────────────────────────────────────────────────────────────
# 2. _composite_score
# ─────────────────────────────────────────────────────────────────────────────

class TestCompositeScore(unittest.TestCase):

    def _make_st(self, direction):
        """Return a supertrend dict with the given direction."""
        return {'direction': direction, 'signal': direction}

    # ── All-buy scenario ─────────────────────────────────────────────────────

    def test_all_buy_signals_strong_buy(self):
        score, label, conf = _composite_score(
            close_price=110, sma200=100,
            boll_signal='buy', rsi_signal='buy',
            stoch_signal='buy', supertrend_signal=self._make_st('bullish'),
        )
        self.assertGreaterEqual(score, 0.5)
        self.assertEqual(label, 'Strong Buy')
        self.assertEqual(conf, 4)

    # ── All-sell scenario ────────────────────────────────────────────────────

    def test_all_sell_signals_strong_sell(self):
        score, label, conf = _composite_score(
            close_price=90, sma200=100,
            boll_signal='sell', rsi_signal='sell',
            stoch_signal='sell', supertrend_signal=self._make_st('bearish'),
        )
        self.assertLessEqual(score, -0.5)
        self.assertEqual(label, 'Strong Sell')
        self.assertEqual(conf, 4)

    # ── Mixed signals → Hold ─────────────────────────────────────────────────

    def test_mixed_signals_hold(self):
        score, label, conf = _composite_score(
            close_price=100, sma200=100,
            boll_signal='buy', rsi_signal='sell',
            stoch_signal='hold', supertrend_signal=self._make_st('bullish'),
        )
        self.assertGreater(score, -0.2)
        self.assertLess(score, 0.2)
        self.assertEqual(label, 'Hold')

    # ── SMA200 influence ─────────────────────────────────────────────────────

    def test_above_sma200_adds_positive_contribution(self):
        score_above, _, _ = _composite_score(
            close_price=110, sma200=100,
            boll_signal='hold', rsi_signal='hold',
            stoch_signal='hold', supertrend_signal=self._make_st('neutral'),
        )
        score_below, _, _ = _composite_score(
            close_price=90, sma200=100,
            boll_signal='hold', rsi_signal='hold',
            stoch_signal='hold', supertrend_signal=self._make_st('neutral'),
        )
        self.assertGreater(score_above, score_below)

    # ── Legacy string supertrend (non-dict) ──────────────────────────────────

    def test_legacy_string_supertrend_rise(self):
        score, label, conf = _composite_score(
            close_price=110, sma200=100,
            boll_signal='buy', rsi_signal='buy',
            stoch_signal='buy', supertrend_signal='stock will rise',
        )
        self.assertGreaterEqual(score, 0.5)
        self.assertEqual(label, 'Strong Buy')

    def test_legacy_string_supertrend_fall(self):
        score, label, conf = _composite_score(
            close_price=90, sma200=100,
            boll_signal='sell', rsi_signal='sell',
            stoch_signal='sell', supertrend_signal='stock will fall',
        )
        self.assertLessEqual(score, -0.5)
        self.assertEqual(label, 'Strong Sell')

    # ── Invalid / empty prices ────────────────────────────────────────────────

    def test_empty_price_strings_do_not_crash(self):
        score, label, conf = _composite_score(
            close_price='', sma200='',
            boll_signal='buy', rsi_signal='buy',
            stoch_signal='buy', supertrend_signal=self._make_st('bullish'),
        )
        # SMA contribution is 0; rest still sums to buy
        self.assertIsInstance(score, float)
        self.assertIn(label, ('Buy', 'Strong Buy'))

    def test_score_rounds_to_3_decimal_places(self):
        score, _, _ = _composite_score(
            close_price=100, sma200=90,
            boll_signal='buy', rsi_signal='sell',
            stoch_signal='hold', supertrend_signal=self._make_st('bullish'),
        )
        self.assertEqual(score, round(score, 3))

    # ── Confidence count ─────────────────────────────────────────────────────

    def test_confidence_counts_agreeing_indicators(self):
        # 3 buy indicators, 1 sell → score positive, confidence = 3
        score, label, conf = _composite_score(
            close_price=110, sma200=100,
            boll_signal='buy', rsi_signal='buy',
            stoch_signal='sell', supertrend_signal=self._make_st('bullish'),
        )
        self.assertGreater(score, 0)
        self.assertEqual(conf, 3)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Env-var helpers (_bool_env, _float_env, _int_env, _list_env)
# ─────────────────────────────────────────────────────────────────────────────

class TestBoolEnv(unittest.TestCase):

    def _set(self, key, val):
        os.environ[key] = val

    def _unset(self, key):
        os.environ.pop(key, None)

    def test_true_string(self):
        self._set('_TEST_BOOL', 'true');  self.assertTrue(_bool_env('_TEST_BOOL'))
    def test_True_capitalised(self):
        self._set('_TEST_BOOL', 'True');  self.assertTrue(_bool_env('_TEST_BOOL'))
    def test_one_string(self):
        self._set('_TEST_BOOL', '1');     self.assertTrue(_bool_env('_TEST_BOOL'))
    def test_yes_string(self):
        self._set('_TEST_BOOL', 'yes');   self.assertTrue(_bool_env('_TEST_BOOL'))
    def test_false_string(self):
        self._set('_TEST_BOOL', 'false'); self.assertFalse(_bool_env('_TEST_BOOL'))
    def test_zero_string(self):
        self._set('_TEST_BOOL', '0');     self.assertFalse(_bool_env('_TEST_BOOL'))
    def test_missing_uses_default(self):
        self._unset('_TEST_BOOL_MISSING')
        self.assertFalse(_bool_env('_TEST_BOOL_MISSING', False))
        self.assertTrue(_bool_env('_TEST_BOOL_MISSING', True))

    def tearDown(self):
        for k in ('_TEST_BOOL', '_TEST_BOOL_MISSING'):
            self._unset(k)


class TestFloatEnv(unittest.TestCase):

    def test_valid_float(self):
        os.environ['_TEST_FLOAT'] = '3.14'
        self.assertAlmostEqual(_float_env('_TEST_FLOAT'), 3.14)

    def test_invalid_uses_default(self):
        os.environ['_TEST_FLOAT'] = 'notanumber'
        self.assertEqual(_float_env('_TEST_FLOAT', 99.9), 99.9)

    def test_missing_uses_default(self):
        os.environ.pop('_TEST_FLOAT_MISSING', None)
        self.assertEqual(_float_env('_TEST_FLOAT_MISSING', 5.0), 5.0)

    def tearDown(self):
        for k in ('_TEST_FLOAT', '_TEST_FLOAT_MISSING'):
            os.environ.pop(k, None)


class TestIntEnv(unittest.TestCase):

    def test_valid_int(self):
        os.environ['_TEST_INT'] = '7'
        self.assertEqual(_int_env('_TEST_INT'), 7)

    def test_invalid_uses_default(self):
        os.environ['_TEST_INT'] = 'abc'
        self.assertEqual(_int_env('_TEST_INT', 42), 42)

    def test_missing_uses_default(self):
        os.environ.pop('_TEST_INT_MISSING', None)
        self.assertEqual(_int_env('_TEST_INT_MISSING', 3), 3)

    def tearDown(self):
        for k in ('_TEST_INT', '_TEST_INT_MISSING'):
            os.environ.pop(k, None)


class TestListEnv(unittest.TestCase):

    def test_valid_json_array(self):
        os.environ['_TEST_LIST'] = '["a@b.com","c@d.com"]'
        self.assertEqual(_list_env('_TEST_LIST'), ['a@b.com', 'c@d.com'])

    def test_invalid_json_uses_default(self):
        os.environ['_TEST_LIST'] = 'not_json'
        self.assertEqual(_list_env('_TEST_LIST', ['x']), ['x'])

    def test_missing_uses_default(self):
        os.environ.pop('_TEST_LIST_MISSING', None)
        self.assertEqual(_list_env('_TEST_LIST_MISSING', ['z']), ['z'])

    def test_empty_string_uses_default(self):
        os.environ['_TEST_LIST'] = ''
        self.assertEqual(_list_env('_TEST_LIST', []), [])

    def tearDown(self):
        for k in ('_TEST_LIST', '_TEST_LIST_MISSING'):
            os.environ.pop(k, None)


# ─────────────────────────────────────────────────────────────────────────────
# 4. 52-week threshold boundary logic (pure arithmetic, no network)
# ─────────────────────────────────────────────────────────────────────────────

class TestFiftyTwoWeekThreshold(unittest.TestCase):
    """
    Verify the percentage-from-52w-high/low formulae used in
    fiftytwo_week_analysis_retriever.py.
    """

    @staticmethod
    def _perc_high(weeks52_high, todays_low):
        """% below 52-week HIGH  →  qualifies when 0 < result < threshold."""
        return ((weeks52_high - todays_low) / weeks52_high) * 100

    @staticmethod
    def _perc_low(weeks52_low, todays_high):
        """% above 52-week LOW   →  qualifies when 0 < result < threshold."""
        return ((todays_high - weeks52_low) / weeks52_low) * 100

    def test_near_52w_high_below_threshold(self):
        # Stock is 5% below its 52w high; threshold is 16% → should qualify
        ph = self._perc_high(weeks52_high=1000, todays_low=950)
        self.assertAlmostEqual(ph, 5.0)
        self.assertGreater(ph, 0)
        self.assertLess(ph, 16)

    def test_near_52w_high_above_threshold(self):
        # Stock is 30% below its 52w high → should NOT qualify
        ph = self._perc_high(weeks52_high=1000, todays_low=700)
        self.assertAlmostEqual(ph, 30.0)
        self.assertGreaterEqual(ph, 16)

    def test_near_52w_low_below_threshold(self):
        # Stock is 4% above 52w low; threshold is 5% → should qualify
        pl = self._perc_low(weeks52_low=500, todays_high=520)
        self.assertAlmostEqual(pl, 4.0)
        self.assertGreater(pl, 0)
        self.assertLess(pl, 5)

    def test_near_52w_low_above_threshold(self):
        # Stock is 20% above 52w low → should NOT qualify
        pl = self._perc_low(weeks52_low=500, todays_high=600)
        self.assertAlmostEqual(pl, 20.0)
        self.assertGreaterEqual(pl, 5)

    def test_exact_52w_high_zero_perc(self):
        # Exactly at 52w high → perc_high = 0 → NOT included (condition is > 0)
        ph = self._perc_high(weeks52_high=1000, todays_low=1000)
        self.assertEqual(ph, 0.0)
        self.assertFalse(ph > 0)

    def test_threshold_selects_correct_category(self):
        # Simulate category → threshold mapping
        thresholds = {'large': 16.0, 'mid': 6.0, 'small': 5.0}
        # 5.5 % below 52w high: qualifies for large (16%) and mid (6%), but not small (5%)
        ph = self._perc_high(weeks52_high=1000, todays_low=945)  # 5.5 %
        self.assertAlmostEqual(ph, 5.5)
        self.assertTrue(0 < ph < thresholds['large'])   # qualifies for large
        self.assertTrue(0 < ph < thresholds['mid'])     # qualifies for mid
        self.assertFalse(0 < ph < thresholds['small'])  # does NOT qualify for small (5.5 >= 5.0)


if __name__ == '__main__':
    unittest.main()
