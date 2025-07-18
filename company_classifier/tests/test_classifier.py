"""Tests for the classifier module."""

import numpy as np
import pandas as pd
import pytest
from sklearn.exceptions import NotFittedError  # type: ignore[import-untyped]

from company_classifier.classifier import CompanyClassifier
from company_classifier.preprocess import CompanyPreprocessor

# Classification values
BAD_FIT = 0
GOOD_FIT = 1
NEED_MORE_INFO = 2


@pytest.fixture
def sample_data():
    """Creates sample data for testing.

    Returns a DataFrame with company data and fit categories where:
    - 0 = bad fit
    - 1 = good fit
    - 2 = need more information
    """
    return pd.DataFrame(
        {
            "type": [
                "startup",
                "bigtech",
                "startup",
                "bigtech",
                "startup",
                "bigtech",
                "startup",
                "bigtech",
            ],
            "total_comp": [
                100000,
                200000,
                150000,
                180000,
                np.nan,
                160000,
                np.nan,
                150000,
            ],
            "base": [80000, 150000, 120000, 140000, np.nan, 130000, np.nan, np.nan],
            "rsu": [10000, 40000, 20000, 30000, np.nan, 20000, np.nan, np.nan],
            "bonus": [10000, 10000, 10000, 10000, np.nan, 10000, np.nan, np.nan],
            "remote_policy": [
                "remote",
                "hybrid",
                "office",
                "remote",
                None,
                "hybrid",
                "remote",
                None,
            ],
            "eng_size": [50, 1000, 100, 800, np.nan, 500, 75, np.nan],
            "total_size": [100, 5000, 200, 4000, np.nan, 2000, 150, np.nan],
            "fit_category": [
                GOOD_FIT,  # Clear good fit - startup with good comp
                BAD_FIT,  # Clear bad fit - bigtech with high comp
                GOOD_FIT,  # Another good fit
                BAD_FIT,  # Another bad fit
                NEED_MORE_INFO,  # All comp data missing
                NEED_MORE_INFO,  # Ambiguous case
                NEED_MORE_INFO,  # Missing comp data
                NEED_MORE_INFO,  # Missing multiple fields
            ],
        }
    )


def test_classifier_init():
    """Tests that the classifier initializes correctly."""
    classifier = CompanyClassifier()
    assert hasattr(classifier, "preprocessor")
    assert hasattr(classifier, "model")
    assert isinstance(classifier.preprocessor, CompanyPreprocessor)


def test_classifier_fit(sample_data):
    """Tests that the classifier fits correctly."""
    classifier = CompanyClassifier()
    X = sample_data.drop("fit_category", axis=1)
    y = sample_data["fit_category"]

    classifier.fit(X, y)
    assert hasattr(classifier, "feature_names_")
    assert hasattr(classifier.model, "classes_")
    assert len(classifier.model.classes_) == 3  # Should have 3 classes


def test_classifier_predict_proba(sample_data):
    """Tests probabilistic predictions."""
    classifier = CompanyClassifier()
    X = sample_data.drop("fit_category", axis=1)
    y = sample_data["fit_category"]

    classifier.fit(X, y)
    probas = classifier.predict_proba(X)

    assert probas.shape == (len(X), 3)  # Three-way classification
    assert np.all((probas >= 0) & (probas <= 1))  # Valid probabilities
    assert np.allclose(probas.sum(axis=1), 1)  # Probabilities sum to 1


def test_classifier_predict(sample_data):
    """Tests predictions for three-way classification."""
    classifier = CompanyClassifier()
    X = sample_data.drop("fit_category", axis=1)
    y = sample_data["fit_category"]

    classifier.fit(X, y)
    predictions = classifier.predict(X)

    assert predictions.shape == (len(X),)
    assert set(predictions).issubset({BAD_FIT, GOOD_FIT, NEED_MORE_INFO})


def test_classifier_feature_importance(sample_data):
    """Tests feature importance calculation."""
    classifier = CompanyClassifier()
    X = sample_data.drop("fit_category", axis=1)
    y = sample_data["fit_category"]

    classifier.fit(X, y)
    importance = classifier.feature_importance()

    assert isinstance(importance, dict)
    assert len(importance) > 0
    assert all(isinstance(v, float) for v in importance.values())
    assert all(v >= 0 for v in importance.values())  # Importance scores are non-negative


def test_classifier_not_fitted():
    """Tests that appropriate errors are raised when classifier is not fitted."""
    classifier = CompanyClassifier()
    X = pd.DataFrame(
        {
            "type": ["startup"],
            "total_comp": [100000],
            "base": [80000],
            "rsu": [10000],
            "bonus": [10000],
            "remote_policy": ["remote"],
            "eng_size": [50],
            "total_size": [100],
        }
    )

    with pytest.raises(NotFittedError):
        classifier.predict(X)

    with pytest.raises(NotFittedError):
        classifier.predict_proba(X)

    with pytest.raises(NotFittedError):
        classifier.feature_importance()


def test_classifier_predicts_need_more_info(sample_data):
    """Tests that the classifier correctly identifies cases needing more information."""
    classifier = CompanyClassifier()
    X = sample_data.drop("fit_category", axis=1)
    y = sample_data["fit_category"]

    classifier.fit(X, y)

    # Create a new sample with missing data
    test_case = pd.DataFrame(
        {
            "type": ["startup"],
            "total_comp": [np.nan],  # Missing compensation
            "base": [np.nan],
            "rsu": [np.nan],
            "bonus": [np.nan],
            "remote_policy": ["remote"],
            "eng_size": [50],
            "total_size": [100],
        }
    )

    prediction = classifier.predict(test_case)
    assert prediction[0] == NEED_MORE_INFO  # Should identify missing data case


@pytest.mark.filterwarnings("ignore:Found unknown categories")
@pytest.mark.filterwarnings("ignore:Precision is ill-defined")
def test_classifier_cross_validation(sample_data):
    """Tests cross-validation functionality."""
    classifier = CompanyClassifier()
    X = sample_data.drop("fit_category", axis=1)
    y = sample_data["fit_category"]

    cv_results = classifier.cross_validate(
        X, y, cv=2
    )  # Use 2 folds due to small sample size

    assert isinstance(cv_results, dict)

    # Check that we have all expected scores
    expected_metrics = [
        "test_accuracy",
        "train_accuracy",
        "test_precision_macro",
        "train_precision_macro",
        "test_recall_macro",
        "train_recall_macro",
        "test_f1_macro",
        "train_f1_macro",
        "test_balanced_accuracy",  # New metric
        "train_balanced_accuracy",  # New metric
    ]
    for metric in expected_metrics:
        assert metric in cv_results
        assert len(cv_results[metric]) == 2  # 2 folds
        assert all(isinstance(score, float) for score in cv_results[metric])
        assert all(0 <= score <= 1 for score in cv_results[metric])

    # Check that training scores are better than or equal to test scores
    # This helps detect if we're overfitting
    assert np.mean(cv_results["train_accuracy"]) >= np.mean(
        cv_results["test_accuracy"]
    ), "Training accuracy should be better than test accuracy.\n"
    "MAY FAIL OCCASIONALLY DUE TO SMALL SAMPLE SIZE! If so, try re-running."
