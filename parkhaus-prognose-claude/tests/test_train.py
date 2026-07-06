import unittest
import warnings

import numpy as np

from data_pipeline import train


class TrainMetricSanitizationTests(unittest.TestCase):
    def test_sanitize_metrics_drops_non_finite_values(self):
        metrics = {"mae": 1.0, "mape": float("nan"), "rmse": float("inf")}

        sanitized = train.sanitize_metrics(metrics)

        self.assertEqual(sanitized["mae"], 1.0)
        self.assertNotIn("mape", sanitized)
        self.assertNotIn("rmse", sanitized)

    def test_mean_absolute_percentage_error_handles_all_zero_targets_without_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = train.mean_absolute_percentage_error(np.array([0, 0]), np.array([0, 0]))

        self.assertTrue(np.isnan(value))
        self.assertEqual([], caught)


if __name__ == "__main__":
    unittest.main()
