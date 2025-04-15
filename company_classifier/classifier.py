"""Company classifier module using Random Forest."""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import NotFittedError

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
        self.preprocessor = CompanyPreprocessor()  # Missing indicators are always added
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

    def feature_importance(self) -> dict[str, float]:
        """Get feature importance scores.

        Returns
        -------
        dict[str, float]
            Dictionary mapping feature names to their importance scores.
        """
        self._check_is_fitted()

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
