"""Script to test classifier with real company data."""

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report

from company_classifier.classifier import (
    BAD_FIT,
    GOOD_FIT,
    NEED_MORE_INFO,
    CompanyClassifier,
)


def load_real_data(csv_path="company_ratings.csv"):
    """Load and prepare real company data."""
    df = pd.read_csv(csv_path)

    # Map text categories to numeric values
    category_map = {"good": GOOD_FIT, "bad": BAD_FIT, "needs_more_info": NEED_MORE_INFO}

    # Extract features used by our classifier
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

    # Convert fit categories to numeric values
    y = df["fit_category"].map(category_map).values

    return X, y


def main():
    """Run classifier test on real data."""
    print("Loading real company data...")
    X, y = load_real_data()

    print(f"\nDataset size: {len(X)} companies")
    print("\nClass distribution:")
    classes, counts = np.unique(y, return_counts=True)
    for cls, count in zip(classes, counts):
        label = {
            GOOD_FIT: "Good fit",
            BAD_FIT: "Bad fit",
            NEED_MORE_INFO: "Need more info",
        }[cls]
        print(f"{label}: {count}")

    print("\nTraining classifier...")
    classifier = CompanyClassifier()
    classifier.fit(X, y)

    # Get predictions
    y_pred = classifier.predict(X)

    print("\nClassification Report:")
    print(
        classification_report(
            y, y_pred, target_names=["Bad fit", "Good fit", "Need more info"]
        )
    )

    print("\nFeature Importance:")
    importance = classifier.feature_importance()
    sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    for feature, score in sorted_features:
        print(f"{feature}: {score:.4f}")


if __name__ == "__main__":
    main()
