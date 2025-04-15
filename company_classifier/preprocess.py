"""
Preprocessing pipeline for company classification.

This module handles data preprocessing for the company fit classifier, including:
- Handling missing values in numeric and categorical features
- Encoding categorical variables
- Scaling numeric features
- Basic feature engineering
"""

from typing import List, Optional, cast

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class CompanyPreprocessor:
    """Preprocesses company data for classification.

    This class handles all data preprocessing steps needed to convert raw company data
    into features suitable for machine learning models.

    Attributes:
        numeric_features: List of numeric column names to process
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
        self._build_pipeline()

    def _build_pipeline(self) -> None:
        """Constructs the preprocessing pipeline."""
        numeric_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )

        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
                (
                    "onehot",
                    OneHotEncoder(
                        drop="first", sparse_output=False, handle_unknown="ignore"
                    ),
                ),
            ]
        )

        self.pipeline = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, self.numeric_features),
                ("cat", categorical_transformer, self.categorical_features),
            ]
        )

    def fit(self, X: pd.DataFrame) -> "CompanyPreprocessor":
        """Fits the preprocessing pipeline to the data.

        Args:
            X: DataFrame containing company features

        Returns:
            self: The fitted preprocessor
        """
        if self.pipeline is None:
            self._build_pipeline()
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
        # Cast to ndarray since we know we set sparse=False in OneHotEncoder
        return cast(np.ndarray, self.pipeline.transform(X))

    def fit_transform(self, X: pd.DataFrame) -> np.ndarray:
        """Fits the pipeline and transforms the data.

        Args:
            X: DataFrame containing company features

        Returns:
            np.ndarray: Preprocessed feature matrix
        """
        return self.fit(X).transform(X)

    def get_feature_names(self) -> List[str]:
        """Gets the names of features after preprocessing.

        Returns:
            List[str]: Names of features after preprocessing, including
                      transformed categorical features
        """
        if self.pipeline is None:
            raise ValueError("Preprocessor must be fitted before getting feature names")

        # Get feature names from the column transformer
        feature_names = []

        # Add numeric feature names (these stay the same)
        feature_names.extend(self.numeric_features)

        # Add transformed categorical feature names
        cat_transformer = self.pipeline.named_transformers_["cat"]
        onehot = cat_transformer.named_steps["onehot"]
        cat_features = onehot.get_feature_names_out(self.categorical_features)
        feature_names.extend(cat_features)

        return feature_names


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
    y = df["fit_category"].to_numpy()  # Convert to numpy array

    # Preprocess features
    preprocessor = CompanyPreprocessor()
    X_processed = preprocessor.fit_transform(X)

    return X_processed, y
