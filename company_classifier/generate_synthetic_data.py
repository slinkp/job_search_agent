#!/usr/bin/env python3

"""
Generate synthetic company data for training the company fit classifier.
Supports both random and LLM-based generation, with configurable train/val/test splits.
"""

import argparse
import csv
import os
import sys
from typing import Dict, List, Optional, TextIO, Tuple

import numpy as np

from company_classifier.synthetic_data import (
    CompanyGenerationConfig,
    HybridCompanyGenerator,
    LLMCompanyGenerator,
    RandomCompanyGenerator,
)


def save_companies_to_csv(
    companies: List[Dict], output_file: str, file: Optional[TextIO] = None
):
    """Save generated companies to CSV in our standard format.

    Args:
        companies: List of company dictionaries to save
        output_file: Path to save to, or description for stdout
        file: Optional file object to write to (e.g. sys.stdout)
    """
    f = file if file is not None else open(output_file, "w", newline="")
    try:
        writer = csv.writer(f)
        # Write header
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
    finally:
        if file is None:  # Only close if we opened it
            f.close()


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
        help="Directory to save the generated data. Ignored if --stdout is used.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Output full dataset to stdout instead of files",
    )
    parser.add_argument(
        "--generator",
        choices=["random", "llm", "hybrid"],
        default="random",
        help="Type of generator to use. 'llm' and 'hybrid' require OPENAI_API_KEY to be set.",
    )
    parser.add_argument(
        "--model",
        choices=[
            "gpt-4-turbo-preview",  # Latest GPT-4, fastest of the 4 series
            "gpt-4-0125-preview",  # Similar capabilities, slightly cheaper
            "gpt-3.5-turbo",  # Much faster and cheaper
        ],
        default="gpt-4-turbo-preview",
        help="OpenAI model to use for LLM generation. Only applicable when --generator is 'llm' or 'hybrid'.",
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

    # Create output directory if needed
    if not args.stdout:
        os.makedirs(args.output_dir, exist_ok=True)

    # Check OpenAI API key if needed
    if args.generator in ["llm", "hybrid"] and not os.getenv("OPENAI_API_KEY"):
        print(
            "Error: OPENAI_API_KEY environment variable must be set for LLM-based generation.",
            file=sys.stderr,
        )
        print("You can either:", file=sys.stderr)
        print("1. Export the key: export OPENAI_API_KEY=your-key-here", file=sys.stderr)
        print("2. Use random generation: --generator random", file=sys.stderr)
        sys.exit(1)

    # Initialize generator
    config = CompanyGenerationConfig()
    if args.generator == "random":
        print("Using random company generator", file=sys.stderr)
        generator = RandomCompanyGenerator(config=config, seed=args.random_seed)
    elif args.generator == "llm":
        print(f"Using LLM-based company generator ({args.model})", file=sys.stderr)
        generator = LLMCompanyGenerator(config=config, model=args.model)
    else:  # hybrid
        print(f"Using hybrid company generator (Random + {args.model})", file=sys.stderr)
        generator = HybridCompanyGenerator(config=config, model=args.model)

    # Generate companies
    print(
        f"\nGenerating {args.num_companies} synthetic companies using {args.generator} generator...",
        file=sys.stderr,
    )
    companies = generator.generate_companies(args.num_companies)

    if args.stdout:
        # Output full dataset to stdout
        save_companies_to_csv(companies, "synthetic data", file=sys.stdout)
    else:
        # Split and save data to files
        train_data, val_data, test_data = split_data(
            companies,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
            random_seed=args.random_seed,
        )

        # Save splits
        print(f"\nSaving data splits to {args.output_dir}/", file=sys.stderr)
        print(f"Train: {len(train_data)} companies", file=sys.stderr)
        print(f"Validation: {len(val_data)} companies", file=sys.stderr)
        print(f"Test: {len(test_data)} companies", file=sys.stderr)

        save_companies_to_csv(
            train_data, os.path.join(args.output_dir, "synthetic_train.csv")
        )
        save_companies_to_csv(
            val_data, os.path.join(args.output_dir, "synthetic_val.csv")
        )
        save_companies_to_csv(
            test_data, os.path.join(args.output_dir, "synthetic_test.csv")
        )

        # Also save full dataset
        save_companies_to_csv(
            companies, os.path.join(args.output_dir, "synthetic_full.csv")
        )
        print("\nDone!", file=sys.stderr)


if __name__ == "__main__":
    main()
