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
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class CompanyPreprocessor:
    """Preprocesses company data for classification.

    This class handles all data preprocessing steps needed to convert raw company data
    into features suitable for machine learning models.

    Attributes:
        comp_features: List of compensation-related numeric features
        size_features: List of size-related numeric features
        categorical_features: List of categorical column names to process
        pipeline: sklearn Pipeline that performs the preprocessing
    """

    def __init__(self):
        self.comp_features: List[str] = [
            "total_comp",
            "base",
            "rsu",
            "bonus",
        ]
        self.size_features: List[str] = [
            "eng_size",
            "total_size",
        ]
        self.categorical_features: List[str] = ["type", "remote_policy"]
        self.pipeline: Optional[ColumnTransformer] = None
        self._build_pipeline()

    def _build_pipeline(self) -> None:
        """Constructs the preprocessing pipeline."""
        # For compensation features, use 0 for missing values and only scale non-missing values
        comp_transformer = make_pipeline(
            SimpleImputer(strategy="constant", fill_value=0, add_indicator=True),
            StandardScaler(),
        )

        # For size features, use median imputation
        size_transformer = make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
        )

        # For categorical features, use unknown imputation and one-hot encoding
        categorical_transformer = make_pipeline(
            SimpleImputer(strategy="constant", fill_value="unknown"),
            OneHotEncoder(drop="first", sparse_output=False, handle_unknown="ignore"),
        )

        # Create separate transformers for each feature type to handle missing indicators
        comp_transformers = [
            (f"comp_{feat}", comp_transformer, [feat]) for feat in self.comp_features
        ]
        size_transformers = [
            (f"size_{feat}", size_transformer, [feat]) for feat in self.size_features
        ]
        cat_transformers = [("cat", categorical_transformer, self.categorical_features)]

        # Combine all transformers
        self.pipeline = ColumnTransformer(
            transformers=comp_transformers + size_transformers + cat_transformers,
            verbose_feature_names_out=False,  # This ensures simpler feature names
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
                      transformed categorical features and missing indicators
        """
        if self.pipeline is None:
            raise ValueError("Preprocessor must be fitted before getting feature names")

        # Get feature names from the pipeline
        feature_names = []

        # Add compensation feature names and their missing indicators
        for feat in self.comp_features:
            feature_names.append(feat)
            feature_names.append(f"{feat}_missing")

        # Add size feature names and their missing indicators
        for feat in self.size_features:
            feature_names.append(feat)
            feature_names.append(f"{feat}_missing")

        # Add categorical feature names
        cat_names = [
            name
            for name in self.pipeline.get_feature_names_out()
            if name.startswith(tuple(self.categorical_features))
        ]
        feature_names.extend(cat_names)

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
