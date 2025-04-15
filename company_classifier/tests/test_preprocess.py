"""Tests for the preprocessing pipeline."""

import numpy as np
import pandas as pd
import pytest

from .. import CompanyPreprocessor, load_and_preprocess_data


@pytest.fixture
def sample_data():
    """Creates a small sample dataset for testing."""
    return pd.DataFrame(
        {
            "type": ["public", "private", "private unicorn", None],
            "total_comp": [400000, None, 300000, 250000],
            "base": [200000, 150000, None, 150000],
            "rsu": [150000, None, 100000, 50000],
            "bonus": [50000, None, 50000, 50000],
            "remote_policy": ["hybrid", "remote", None, "office"],
            "eng_size": [100, None, 50, 30],
            "total_size": [1000, 500, None, 300],
            "fit_category": ["good", "bad", "needs_more_info", "good"],
        }
    )


def test_preprocessor_init():
    """Test that preprocessor initializes correctly."""
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


def test_preprocessor_fit(sample_data):
    """Test fitting the preprocessor."""
    preprocessor = CompanyPreprocessor()
    preprocessor.fit(sample_data)
    # Verify the pipeline was fitted
    assert preprocessor.pipeline is not None
    assert hasattr(preprocessor.pipeline, "n_features_in_")


def test_preprocessor_transform(sample_data):
    """Test transforming data with the preprocessor."""
    preprocessor = CompanyPreprocessor()
    X_transformed = preprocessor.fit_transform(sample_data)

    # Get actual feature names to verify shape
    feature_names = preprocessor.get_feature_names()
    assert X_transformed.shape == (len(sample_data), len(feature_names))

    # Check that output is scaled (numeric features should have mean close to 0)
    numeric_features = X_transformed[:, : len(preprocessor.numeric_features)]
    assert np.abs(numeric_features.mean()) < 1e-10


def test_get_feature_names(sample_data):
    """Test getting feature names after transformation."""
    preprocessor = CompanyPreprocessor()
    preprocessor.fit_transform(sample_data)
    feature_names = preprocessor.get_feature_names()

    # We should have:
    # - All numeric features
    # - Encoded categorical features (excluding first category for each)
    assert len(feature_names) > len(preprocessor.numeric_features)
    assert all(f in feature_names for f in preprocessor.numeric_features)


def test_load_and_preprocess_data(tmp_path, sample_data):
    """Test loading and preprocessing data from CSV."""
    # Save sample data to temporary CSV
    csv_path = tmp_path / "test_companies.csv"
    sample_data.to_csv(csv_path, index=False)

    # Load and preprocess
    X, y = load_and_preprocess_data(str(csv_path))

    # Check shapes
    assert len(X) == len(sample_data)
    assert len(y) == len(sample_data)

    # Check target values
    expected_classes = ["good", "bad", "needs_more_info"]
    assert all(yi in expected_classes for yi in y)


def test_preprocessor_with_missing_values(sample_data):
    """Test that preprocessor handles missing values correctly."""
    preprocessor = CompanyPreprocessor()
    X_transformed = preprocessor.fit_transform(sample_data)

    # Check that there are no NaN values in output
    assert not np.isnan(X_transformed).any()


def test_preprocessor_with_new_categories():
    """Test handling of new categories at transform time."""
    # Training data
    train_data = pd.DataFrame(
        {
            "type": ["public", "private"],
            "total_comp": [400000, 300000],
            "base": [200000, 150000],
            "rsu": [150000, 100000],
            "bonus": [50000, 50000],
            "remote_policy": ["hybrid", "remote"],
            "eng_size": [100, 50],
            "total_size": [1000, 500],
        }
    )

    # Test data with new category
    test_data = pd.DataFrame(
        {
            "type": ["private unicorn"],  # New category
            "total_comp": [350000],
            "base": [175000],
            "rsu": [125000],
            "bonus": [50000],
            "remote_policy": ["office"],  # New category
            "eng_size": [75],
            "total_size": [750],
        }
    )

    preprocessor = CompanyPreprocessor()
    preprocessor.fit(train_data)

    # Should not raise an error
    X_transformed = preprocessor.transform(test_data)
    assert X_transformed.shape[0] == len(test_data)

    # New categories should be encoded as all zeros
    feature_names = preprocessor.get_feature_names()
    categorical_start = len(preprocessor.numeric_features)
    categorical_features = X_transformed[:, categorical_start:]
    assert np.allclose(categorical_features, 0)
