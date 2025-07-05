"""
Preprocessing pipeline for company classification.

This module handles data preprocessing for the company fit classifier, including:
- Handling missing values in numeric and categorical features
- Encoding categorical variables
- Normalizing remote policy values
"""

from typing import List, Optional, Union, cast

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder


class RemotePolicyNormalizer(BaseEstimator, TransformerMixin):
    """Normalizes remote policy values to standard categories."""

    def fit(self, X, y=None):
        """Nothing to fit, just for sklearn compatibility."""
        return self

    def transform(self, X: Union[pd.Series, np.ndarray]) -> pd.Series:
        """Normalizes remote policy values to standard categories."""

        def standardize_policy(policy: str) -> str:
            policy = str(policy).lower()
            policy = "-".join(policy.split())
            if "hybrid" in policy or "day" in policy or "some" in policy:
                return "hybrid"
            if "remote" in policy:
                return "remote"
            if "office" in policy or "onsite" in policy or "in-person" in policy:
                return "office"
            if "relocation" in policy:
                return "relocation"
            return policy

        if isinstance(X, np.ndarray):
            X = pd.Series(X.ravel())

        return X.apply(standardize_policy)


class CompanyPreprocessor(BaseEstimator, TransformerMixin):
    """Preprocesses company data for classification.

    This class handles all data preprocessing steps needed to convert raw company data
    into features suitable for machine learning models.

    Attributes:
        numeric_features: List of numeric features to process
        categorical_features: List of categorical column names to process
        pipeline: sklearn Pipeline that performs the preprocessing
    """

    def __init__(self):
        self.numeric_features: List[str] = [
            "total_comp",
            "base",
            "rsu",
            "bonus",
            "eng_size",
            "total_size",
        ]
        self.categorical_features: List[str] = ["type", "remote_policy"]
        self.pipeline: Optional[ColumnTransformer] = None
        self.remote_policy_normalizer = RemotePolicyNormalizer()
        self._build_pipeline()

    def _build_pipeline(self) -> None:
        """Constructs the preprocessing pipeline."""
        # For numeric features, use 0 for missing values and add missing indicators
        numeric_transformer = SimpleImputer(
            strategy="constant", fill_value=0, add_indicator=True
        )

        # handle_unknown='ignore' will encode unknown categories as all zeros
        categorical_transformer = OneHotEncoder(
            drop="first",
            sparse_output=False,
            handle_unknown="ignore",
        )

        self.pipeline = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, self.numeric_features),
                ("cat", categorical_transformer, self.categorical_features),
            ],
            verbose_feature_names_out=True,
        )

    def fit(self, X: pd.DataFrame, y=None) -> "CompanyPreprocessor":
        """Fits the preprocessing pipeline to the data.

        Args:
            X: DataFrame containing company features
            y: Ignored. Present for scikit-learn compatibility.

        Returns:
            self: The fitted preprocessor
        """
        if self.pipeline is None:
            self._build_pipeline()

        # First normalize remote policy values
        X = X.copy()
        X["remote_policy"] = self.remote_policy_normalizer.fit_transform(
            X["remote_policy"]
        )

        assert self.pipeline is not None  # for type checker
        self.pipeline.fit(X)
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """Transforms raw company data into preprocessed features.

        Args:
            X: DataFrame containing company features

        Returns:
            np.ndarray: Preprocessed feature matrix
        """
        if self.pipeline is None:
            raise ValueError("Preprocessor must be fitted before transform")

        # First normalize remote policy values
        X = X.copy()
        X["remote_policy"] = self.remote_policy_normalizer.transform(X["remote_policy"])

        return cast(np.ndarray, self.pipeline.transform(X))

    def get_feature_names(self) -> List[str]:
        """Gets the names of features after preprocessing.

        Returns:
            List[str]: Names of features after preprocessing
        """
        if self.pipeline is None:
            raise ValueError("Preprocessor must be fitted before getting feature names")
        return self.pipeline.get_feature_names_out().tolist()


def load_and_preprocess_data(csv_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Loads and preprocesses company data from CSV.

    Args:
        csv_path: Path to the CSV file containing company data

    Returns:
        tuple[np.ndarray, np.ndarray]: Tuple of (X, y) where X is the preprocessed
        feature matrix and y is the target vector
    """
    # Load data
    df = pd.read_csv(csv_path)

    # Extract features and target
    X = df[
        [
            "type",
            "total_comp",
            "base",
            "rsu",
            "bonus",
            "remote_policy",
            "eng_size",
            "total_size",
        ]
    ]
    y = df["fit_category"].to_numpy()

    # Preprocess features
    preprocessor = CompanyPreprocessor()
    X_processed = preprocessor.fit_transform(X)

    return X_processed, y
