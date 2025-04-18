#!/usr/bin/env python3

"""
Generate synthetic company data for training the company fit classifier.
Supports both random and LLM-based generation, with configurable train/val/test splits.
"""

import argparse
import csv
import os
from typing import Dict, List, Tuple

import numpy as np

from company_classifier.synthetic_data import (
    CompanyGenerationConfig,
    HybridCompanyGenerator,
    LLMCompanyGenerator,
    RandomCompanyGenerator,
)


def save_companies_to_csv(companies: List[Dict], output_file: str):
    """Save generated companies to CSV in our standard format."""
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        # Write header (matching company_ratings.csv format)
        writer.writerow(
            [
                "company_id",
                "name",
                "type",
                "valuation",
                "total_comp",
                "base",
                "rsu",
                "bonus",
                "remote_policy",
                "eng_size",
                "total_size",
                "headquarters",
                "ny_address",
                "ai_notes",
                "fit_category",
                "fit_confidence",
            ]
        )

        # Write data
        for company in companies:
            writer.writerow(
                [
                    company["company_id"],
                    company["name"],
                    company["type"],
                    company["valuation"],
                    company["total_comp"],
                    company["base"],
                    company["rsu"],
                    company["bonus"],
                    company["remote_policy"],
                    company["eng_size"],
                    company["total_size"],
                    company["headquarters"],
                    company["ny_address"],
                    company["ai_notes"],
                    company["fit_category"],
                    company["fit_confidence"],
                ]
            )


def split_data(
    companies: List[Dict],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Split companies into train, validation, and test sets."""
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-10, "Ratios must sum to 1"

    # Shuffle with fixed seed for reproducibility
    rng = np.random.RandomState(random_seed)
    indices = np.arange(len(companies))
    rng.shuffle(indices)

    # Calculate split points
    train_end = int(len(companies) * train_ratio)
    val_end = int(len(companies) * (train_ratio + val_ratio))

    # Split the data
    train = [companies[i] for i in indices[:train_end]]
    val = [companies[i] for i in indices[train_end:val_end]]
    test = [companies[i] for i in indices[val_end:]]

    return train, val, test


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic company data for training"
    )

    parser.add_argument(
        "--num-companies",
        type=int,
        default=1000,
        help="Number of synthetic companies to generate",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/synthetic",
        help="Directory to save the generated data",
    )
    parser.add_argument(
        "--generator",
        choices=["random", "llm", "hybrid"],
        default="random",
        help="Type of generator to use",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.7, help="Ratio of data to use for training"
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.15,
        help="Ratio of data to use for validation",
    )
    parser.add_argument(
        "--test-ratio", type=float, default=0.15, help="Ratio of data to use for testing"
    )
    parser.add_argument(
        "--random-seed", type=int, default=42, help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize generator
    config = CompanyGenerationConfig()
    if args.generator == "random":
        generator = RandomCompanyGenerator(config=config, seed=args.random_seed)
    elif args.generator == "llm":
        generator = LLMCompanyGenerator(config=config)
    else:  # hybrid
        generator = HybridCompanyGenerator(config=config)

    # Generate companies
    print(
        f"Generating {args.num_companies} synthetic companies using {args.generator} generator..."
    )
    companies = generator.generate_companies(args.num_companies)

    # Split data
    train_data, val_data, test_data = split_data(
        companies,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        random_seed=args.random_seed,
    )

    # Save splits
    print(f"\nSaving data splits to {args.output_dir}/")
    print(f"Train: {len(train_data)} companies")
    print(f"Validation: {len(val_data)} companies")
    print(f"Test: {len(test_data)} companies")

    save_companies_to_csv(
        train_data, os.path.join(args.output_dir, "synthetic_train.csv")
    )
    save_companies_to_csv(val_data, os.path.join(args.output_dir, "synthetic_val.csv"))
    save_companies_to_csv(test_data, os.path.join(args.output_dir, "synthetic_test.csv"))

    # Also save full dataset
    save_companies_to_csv(companies, os.path.join(args.output_dir, "synthetic_full.csv"))
    print("\nDone!")


if __name__ == "__main__":
    main()
