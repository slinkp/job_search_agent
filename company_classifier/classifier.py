"""Company classifier module using Random Forest."""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import NotFittedError
from sklearn.model_selection import cross_validate
from sklearn.pipeline import Pipeline

from .preprocess import CompanyPreprocessor

# Classification values
BAD_FIT = 0
GOOD_FIT = 1
NEED_MORE_INFO = 2


class CompanyClassifier:
    """Classifier for determining company fit using Random Forest.

    This classifier combines preprocessing of company data with a Random Forest
    model to predict whether a company is a good fit, bad fit, or needs more information.

    Classification values:
    - 0: Bad fit
    - 1: Good fit
    - 2: Need more information
    """

    def __init__(self, random_state=42):
        """Initialize the classifier.

        Parameters
        ----------
        random_state : int, default=42
            Random state for reproducibility.
        """
        self.preprocessor = CompanyPreprocessor()
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=None,  # Let trees grow fully
            min_samples_split=2,
            min_samples_leaf=1,
            class_weight={
                BAD_FIT: 1.0,
                GOOD_FIT: 1.0,
                NEED_MORE_INFO: 2.0,  # Give more weight to "need more info" class
            },
            random_state=random_state,
            n_jobs=-1,  # Use all available cores
        )
        self.feature_names_ = None
        self._pipeline = None

    @property
    def pipeline(self):
        """Get the scikit-learn pipeline combining preprocessing and classification.

        Returns
        -------
        Pipeline
            The scikit-learn pipeline
        """
        if self._pipeline is None:
            self._pipeline = Pipeline(
                [("preprocessor", self.preprocessor), ("classifier", self.model)]
            )
        return self._pipeline

    def fit(self, X, y):
        """Fit the classifier to training data.

        Parameters
        ----------
        X : pandas.DataFrame
            Training data features
        y : array-like
            Target values:
            - 0: Bad fit
            - 1: Good fit
            - 2: Need more information

        Returns
        -------
        self : CompanyClassifier
            The fitted classifier
        """
        # Transform features
        X_transformed = self.preprocessor.fit_transform(X)
        self.feature_names_ = self.preprocessor.get_feature_names()

        # Fit the model
        self.model.fit(X_transformed, y)
        return self

    def predict_proba(self, X):
        """Predict class probabilities for X.

        Parameters
        ----------
        X : pandas.DataFrame
            The input samples

        Returns
        -------
        array-like of shape (n_samples, 3)
            The class probabilities for each sample.
            Columns represent probabilities for:
            - Bad fit (0)
            - Good fit (1)
            - Need more information (2)
        """
        self._check_is_fitted()
        X_transformed = self.preprocessor.transform(X)
        return self.model.predict_proba(X_transformed)

    def predict(self, X):
        """Predict classes for X.

        Parameters
        ----------
        X : pandas.DataFrame
            The input samples

        Returns
        -------
        array-like of shape (n_samples,)
            The predicted classes:
            - 0: Bad fit
            - 1: Good fit
            - 2: Need more information
        """
        self._check_is_fitted()
        X_transformed = self.preprocessor.transform(X)

        # Get probabilities
        probas = self.model.predict_proba(X_transformed)

        # If we have high uncertainty (no class probability > 0.5)
        # or significant missing data, predict NEED_MORE_INFO
        predictions = self.model.predict(X_transformed)
        max_probas = np.max(probas, axis=1)

        # Override predictions with NEED_MORE_INFO where we're uncertain
        predictions[max_probas < 0.5] = NEED_MORE_INFO

        return predictions

    def cross_validate(self, X, y, cv=5, scoring=None):
        """Perform cross-validation to evaluate the classifier.

        Parameters
        ----------
        X : pandas.DataFrame
            The input samples
        y : array-like
            The target values
        cv : int, default=5
            Number of folds for cross-validation
        scoring : str or list of str, default=None
            Scoring metrics to compute. If None, computes:
            - 'accuracy': Standard accuracy
            - 'balanced_accuracy': Accuracy that accounts for class imbalance
            - 'precision_macro': Precision averaged over all classes
            - 'recall_macro': Recall averaged over all classes
            - 'f1_macro': F1 score averaged over all classes

        Returns
        -------
        dict
            Dictionary containing cross-validation results:
            - test_*: Test scores for each metric
            - train_*: Training scores for each metric
            Each value is an array of scores, one per fold
        """
        if scoring is None:
            scoring = [
                "accuracy",
                "balanced_accuracy",
                "precision_macro",
                "recall_macro",
                "f1_macro",
            ]

        cv_results = cross_validate(
            self.pipeline, X, y, cv=cv, scoring=scoring, return_train_score=True
        )

        return cv_results

    def feature_importance(self) -> dict[str, float]:
        """Get feature importance scores.

        Returns
        -------
        dict[str, float]
            Dictionary mapping feature names to their importance scores.
        """
        self._check_is_fitted()
        assert self.feature_names_ is not None

        return dict(zip(self.feature_names_, self.model.feature_importances_))

    def _check_is_fitted(self):
        """Check if the classifier is fitted.

        Raises
        ------
        NotFittedError
            If the classifier is not fitted yet.
        """
        if not hasattr(self, "feature_names_") or self.feature_names_ is None:
            raise NotFittedError(
                "This CompanyClassifier instance is not fitted yet. "
                "Call 'fit' with appropriate arguments before using this estimator."
            )
