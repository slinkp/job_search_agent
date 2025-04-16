"""Script to test classifier with real company data."""

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from company_classifier.classifier import (
    BAD_FIT,
    GOOD_FIT,
    NEED_MORE_INFO,
    CompanyClassifier,
)


def load_real_data(csv_path: str) -> tuple[pd.DataFrame, np.ndarray]:
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
    y = df["fit_category"].map(category_map).to_numpy()

    return X, y


def main(csv_path: str):
    """Run classifier test on real data."""
    print("Loading real company data...")
    X, y = load_real_data(csv_path)

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

    # First, let's do a train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("\nSplit sizes:")
    print(f"Training set: {len(X_train)} companies")
    print(f"Test set: {len(X_test)} companies")

    print("\nTraining and evaluating classifier...")
    classifier = CompanyClassifier()

    # Train on training set
    classifier.fit(X_train, y_train)

    # Predict on test set
    y_pred = classifier.predict(X_test)

    print("\nTest Set Performance:")
    print(
        classification_report(
            y_test, y_pred, target_names=["Bad fit", "Good fit", "Need more info"]
        )
    )

    print("\nPerforming cross-validation...")
    cv_results = classifier.cross_validate(
        X, y, cv=5, scoring=["accuracy", "precision_macro", "recall_macro", "f1_macro"]
    )

    print("\nCross-validation results:")
    print(
        f"CV Accuracy: {cv_results['test_accuracy'].mean():.2f} (+/- {cv_results['test_accuracy'].std() * 2:.2f})"
    )
    print(
        f"CV Precision: {cv_results['test_precision_macro'].mean():.2f} (+/- {cv_results['test_precision_macro'].std() * 2:.2f})"
    )
    print(
        f"CV Recall: {cv_results['test_recall_macro'].mean():.2f} (+/- {cv_results['test_recall_macro'].std() * 2:.2f})"
    )
    print(
        f"CV F1: {cv_results['test_f1_macro'].mean():.2f} (+/- {cv_results['test_f1_macro'].std() * 2:.2f})"
    )

    print("\nTraining vs Test Performance:")
    print(f"Training Accuracy: {cv_results['train_accuracy'].mean():.2f}")
    print(f"Test Accuracy: {cv_results['test_accuracy'].mean():.2f}")

    print("\nFeature Importance (from full model):")
    classifier.fit(X, y)  # Refit on full dataset for feature importance
    importance = classifier.feature_importance()
    sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    for feature, score in sorted_features:
        print(f"{feature}: {score:.4f}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_path", type=str, default="company_ratings.csv")
    args = parser.parse_args()
    main(args.csv_path)
