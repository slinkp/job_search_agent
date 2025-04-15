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
    assert preprocessor.comp_features == [
        "total_comp",
        "base",
        "rsu",
        "bonus",
    ]
    assert preprocessor.size_features == ["eng_size", "total_size"]
    assert preprocessor.categorical_features == ["type", "remote_policy"]
    assert preprocessor.pipeline is not None


def test_preprocessor_transform(sample_data):
    """Tests that the preprocessor transforms data correctly."""
    preprocessor = CompanyPreprocessor()
    X_transformed = preprocessor.fit_transform(sample_data)

    # Print debug information
    print("\nTransformed data shape:", X_transformed.shape)
    print("\nFeature names:", preprocessor.get_feature_names())

    # Print unique values in categorical columns
    print("\nUnique values in 'type':", sample_data["type"].unique())
    print("Unique values in 'remote_policy':", sample_data["remote_policy"].unique())

    # Calculate expected number of features:
    # - Compensation features (4) + their missing indicators (4)
    # - Size features (2) + their missing indicators (2)
    # - Categorical features after one-hot encoding with drop="first":
    #   - type: 2 categories - 1 = 1 feature
    #   - remote_policy: 3 categories - 1 = 2 features
    expected_features = (
        len(preprocessor.comp_features) * 2  # comp features + missing indicators
        + len(preprocessor.size_features) * 2  # size features + missing indicators
        + 1  # type (startup, bigtech - 1)
        + 2  # remote_policy (remote, hybrid, office - 1)
    )

    # Print the breakdown of expected features
    print("\nExpected feature breakdown:")
    print(f"Compensation features + indicators: {len(preprocessor.comp_features) * 2}")
    print(f"Size features + indicators: {len(preprocessor.size_features) * 2}")
    print("Categorical features after one-hot: 3")
    print(f"Total expected: {expected_features}")

    assert X_transformed.shape == (3, expected_features)

    # Check that numeric features are standardized
    size_features_start = (
        len(preprocessor.comp_features) * 2
    )  # including missing indicators
    size_features_end = size_features_start + len(preprocessor.size_features)
    size_features = X_transformed[:, size_features_start:size_features_end]
    assert np.allclose(size_features.mean(axis=0), 0, atol=1e-10)
    assert np.allclose(size_features.std(axis=0), 1, atol=1e-10)


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

    # Check that missing compensation values are 0
    comp_features_end = len(preprocessor.comp_features)
    missing_indicators = X_transformed[:, comp_features_end : comp_features_end * 2]
    comp_values = X_transformed[:, :comp_features_end]
    assert np.all(comp_values[missing_indicators == 1] == 0)

    # Check that size features use median imputation
    size_features_start = len(preprocessor.comp_features) * 2
    size_features_end = size_features_start + len(preprocessor.size_features)
    size_values = X_transformed[:, size_features_start:size_features_end]
    assert not np.any(np.isnan(size_values))

    # Check that categorical features use "unknown" imputation
    cat_features_start = size_features_end + len(preprocessor.size_features)
    cat_values = X_transformed[:, cat_features_start:]
    assert not np.any(np.isnan(cat_values))


def test_preprocessor_with_new_categories():
    """Tests that the preprocessor handles new categories correctly."""
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
            "type": ["new_type"],
            "total_comp": [300000],
            "base": [200000],
            "rsu": [80000],
            "bonus": [20000],
            "remote_policy": ["new_policy"],
            "eng_size": [2000],
            "total_size": [10000],
        }
    )

    preprocessor = CompanyPreprocessor()
    preprocessor.fit(train_data)
    X_transformed = preprocessor.transform(test_data)

    # Get the start index of categorical features
    cat_start = (
        len(preprocessor.comp_features) * 2  # comp features + missing indicators
        + len(preprocessor.size_features) * 2  # size features + missing indicators
    )

    # Check that new categories are encoded as all zeros
    cat_values = X_transformed[:, cat_start:]
    assert np.all(cat_values == 0)


def test_get_feature_names():
    """Tests that feature names are generated correctly."""
    data = pd.DataFrame(
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

    preprocessor = CompanyPreprocessor()
    preprocessor.fit(data)
    feature_names = preprocessor.get_feature_names()

    # Check that we have the expected number of numeric features and their missing indicators
    expected_numeric_features = (
        len(preprocessor.comp_features) * 2  # comp features + missing indicators
        + len(preprocessor.size_features) * 2  # size features + missing indicators
    )

    # Verify that the number of numeric features matches
    numeric_feature_names = [
        name
        for name in feature_names
        if not name.startswith(tuple(preprocessor.categorical_features))
    ]
    assert len(numeric_feature_names) == expected_numeric_features

    # Verify that categorical feature names exist for each category (minus one per feature due to drop="first")
    cat_feature_names = [
        name
        for name in feature_names
        if name.startswith(tuple(preprocessor.categorical_features))
    ]
    assert len(cat_feature_names) > 0

    # Check that all feature names are unique
    assert len(feature_names) == len(set(feature_names))


def test_load_and_preprocess_data(tmp_path):
    """Tests the data loading and preprocessing function."""
    # Create a temporary CSV file
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
    assert y.dtype == np.int64  # Check that target is integer type
