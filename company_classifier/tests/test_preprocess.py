"""Tests for the preprocessing module."""

import numpy as np
import pandas as pd
import pytest

from company_classifier.preprocess import CompanyPreprocessor


@pytest.fixture
def sample_data():
    """Creates sample data for testing."""
    return pd.DataFrame(
        {
            "type": ["startup", "bigtech", "startup"],
            "total_comp": [100000, 200000, 150000],
            "base": [80000, 150000, 120000],
            "rsu": [10000, 40000, 20000],
            "bonus": [10000, 10000, 10000],
            "remote_policy": ["remote", "hybrid", "office"],
            "eng_size": [50, 1000, 100],
            "total_size": [100, 5000, 200],
        }
    )


def test_preprocessor_init():
    """Tests that the preprocessor initializes correctly."""
    preprocessor = CompanyPreprocessor()
    assert preprocessor.numeric_features == [
        "total_comp",
        "base",
        "rsu",
        "bonus",
        "eng_size",
        "total_size",
    ]
    assert preprocessor.categorical_features == ["type", "remote_policy"]
    assert preprocessor.pipeline is not None


def test_preprocessor_transform(sample_data):
    """Tests that the preprocessor transforms data correctly."""
    preprocessor = CompanyPreprocessor()
    X_transformed = preprocessor.fit_transform(sample_data)

    # Basic shape checks
    assert X_transformed.shape[0] == len(sample_data)
    assert not np.any(np.isnan(X_transformed))  # No NaN values

    # Check feature names are as expected
    feature_names = preprocessor.get_feature_names()
    print("\nFeature names:", feature_names)  # Keep debug print for now

    # Verify all our original features are represented somehow
    for feature in preprocessor.numeric_features:
        assert any(
            f"num__{feature}" in name for name in feature_names
        ), f"Feature {feature} not found in {feature_names}"

    for feature in preprocessor.categorical_features:
        assert any(
            f"cat__{feature}" in name for name in feature_names
        ), f"Feature {feature} not found in {feature_names}"


def test_preprocessor_with_missing_values():
    """Tests that the preprocessor handles missing values correctly."""
    data = pd.DataFrame(
        {
            "type": ["startup", None, "startup"],
            "total_comp": [100000, np.nan, 150000],
            "base": [80000, np.nan, 120000],
            "rsu": [10000, np.nan, 20000],
            "bonus": [10000, np.nan, 10000],
            "remote_policy": ["remote", None, "office"],
            "eng_size": [50, np.nan, 100],
            "total_size": [100, np.nan, 200],
        }
    )

    preprocessor = CompanyPreprocessor()
    X_transformed = preprocessor.fit_transform(data)

    # Check no NaN values in output
    assert not np.any(np.isnan(X_transformed))


def test_preprocessor_with_unknown_categories():
    """Tests that the preprocessor errors on unknown categories."""
    train_data = pd.DataFrame(
        {
            "type": ["startup", "bigtech"],
            "total_comp": [100000, 200000],
            "base": [80000, 150000],
            "rsu": [10000, 40000],
            "bonus": [10000, 10000],
            "remote_policy": ["remote", "hybrid"],
            "eng_size": [50, 1000],
            "total_size": [100, 5000],
        }
    )

    test_data = pd.DataFrame(
        {
            "type": ["new_type"],  # New category
            "total_comp": [300000],
            "base": [200000],
            "rsu": [80000],
            "bonus": [20000],
            "remote_policy": ["new_policy"],  # New category
            "eng_size": [2000],
            "total_size": [10000],
        }
    )

    preprocessor = CompanyPreprocessor()
    preprocessor.fit(train_data)

    # Should raise an error due to unknown categories
    with pytest.raises(ValueError):
        preprocessor.transform(test_data)


def test_load_and_preprocess_data(tmp_path):
    """Tests the data loading and preprocessing function."""
    csv_path = tmp_path / "test_data.csv"
    pd.DataFrame(
        {
            "type": ["startup", "bigtech"],
            "total_comp": [100000, 200000],
            "base": [80000, 150000],
            "rsu": [10000, 40000],
            "bonus": [10000, 10000],
            "remote_policy": ["remote", "hybrid"],
            "eng_size": [50, 1000],
            "total_size": [100, 5000],
            "fit_category": [1, 0],
        }
    ).to_csv(csv_path, index=False)

    from company_classifier.preprocess import load_and_preprocess_data

    X, y = load_and_preprocess_data(str(csv_path))
    assert isinstance(X, np.ndarray)
    assert isinstance(y, np.ndarray)
    assert X.shape[0] == y.shape[0]
    assert y.dtype == np.int64
