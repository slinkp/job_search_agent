#!/usr/bin/env python3

"""
Compare different synthetic data generators by generating test batches
and scoring their realism and variety.
"""

import argparse
import csv
import json
import os
import sys
from typing import Literal

from company_classifier.generate_synthetic_data import (
    CompanyGenerationConfig,
    HybridCompanyGenerator,
    LLMCompanyGenerator,
    RandomCompanyGenerator,
    save_companies_to_csv,
)
from company_classifier.score_synthetic_data import calculate_diversity_score


def generate_test_batch(
    generator_type: str,
    num_companies: int,
    provider: Literal["openai", "anthropic"] = "openai",
    model: str = "gpt-4-turbo-preview",
    output_dir: str = "data/synthetic/test_batches",
) -> str:
    """Generate a test batch using the specified generator.

    Args:
        generator_type: One of "random", "llm", or "hybrid"
        num_companies: Number of companies to generate
        provider: LLM provider to use ("openai" or "anthropic")
        model: Model to use for LLM-based generation
        output_dir: Directory to save the generated data

    Returns:
        Path to the generated CSV file
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Initialize generator
    config = CompanyGenerationConfig()
    if generator_type == "random":
        generator = RandomCompanyGenerator(config=config)
    elif generator_type == "llm":
        generator = LLMCompanyGenerator(config=config, model=model, provider=provider)
    else:  # hybrid
        generator = HybridCompanyGenerator(config=config, model=model, provider=provider)

    # Generate companies
    print(f"\nGenerating {num_companies} companies using {generator_type} generator...")
    companies = generator.generate_companies(num_companies)

    # Save to CSV
    output_file = os.path.join(
        output_dir,
        f"{generator_type}_{provider}_{model.replace('.', '_')}_test_batch.csv",
    )
    save_companies_to_csv(companies, output_file)

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Compare different synthetic data generators"
    )
    parser.add_argument(
        "--num-companies",
        type=int,
        default=20,
        help="Number of companies to generate per generator",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/synthetic/test_batches",
        help="Directory to save generated data and comparison results",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM provider to use",
    )
    parser.add_argument(
        "--model",
        default="gpt-4-turbo-preview",
        help="Model to use for LLM-based generation. For OpenAI: gpt-4-turbo-preview, gpt-4-0125-preview, gpt-3.5-turbo. For Anthropic: claude-3-opus-20240229, claude-3-sonnet-20240229",
    )
    args = parser.parse_args()

    # Validate model based on provider
    if args.provider == "openai":
        valid_models = ["gpt-4-turbo-preview", "gpt-4-0125-preview", "gpt-3.5-turbo"]
        if args.model not in valid_models:
            print(
                f"Error: Invalid model for OpenAI provider. Must be one of: {', '.join(valid_models)}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:  # anthropic
        valid_models = ["claude-3-opus-20240229", "claude-3-sonnet-20240229"]
        if args.model not in valid_models:
            print(
                f"Error: Invalid model for Anthropic provider. Must be one of: {', '.join(valid_models)}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Generate test batches
    results = {}
    for generator_type in ["random", "llm", "hybrid"]:
        try:
            output_file = generate_test_batch(
                generator_type,
                args.num_companies,
                provider=args.provider,
                model=args.model,
                output_dir=args.output_dir,
            )

            # Calculate scores
            with open(output_file, "r") as f:
                reader = csv.DictReader(f)
                companies = []
                for row in reader:
                    # Convert numeric fields
                    for field in [
                        "valuation",
                        "total_comp",
                        "base",
                        "rsu",
                        "bonus",
                        "eng_size",
                        "total_size",
                    ]:
                        if row[field]:
                            row[field] = float(row[field])
                        else:
                            row[field] = None
                    companies.append(row)

            scores = calculate_diversity_score(companies)
            results[generator_type] = {
                "scores": scores,
                "output_file": output_file,
            }

        except Exception as e:
            print(f"Error generating {generator_type} test batch: {e}", file=sys.stderr)
            results[generator_type] = {
                "error": str(e),
            }

    # Save comparison results
    results_file = os.path.join(
        args.output_dir,
        f"generator_comparison_{args.provider}_{args.model.replace('.', '_')}.json",
    )
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\nGenerator Comparison Results:")
    print("=" * 50)
    print(f"Provider: {args.provider}")
    print(f"Model: {args.model}")
    print("=" * 50)
    for generator_type, result in results.items():
        print(f"\n{generator_type.upper()} Generator:")
        if "error" in result:
            print(f"  Error: {result['error']}")
        else:
            print(f"  Output file: {result['output_file']}")
            print("  Scores:")
            for metric, score in result["scores"].items():
                print(f"    {metric}: {score:.2f}")

    print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    main()
