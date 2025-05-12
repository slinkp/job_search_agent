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
from typing import Dict, Literal, Tuple

from company_classifier.generate_synthetic_data import (
    CompanyGenerationConfig,
    HybridCompanyGenerator,
    LLMCompanyGenerator,
    RandomCompanyGenerator,
    save_companies_to_csv,
)
from company_classifier.score_synthetic_data import calculate_diversity_score

# Model name mappings and provider inference
MODEL_MAPPINGS: Dict[str, Tuple[str, Literal["openai", "anthropic"]]] = {
    # Anthropic models
    "haiku": ("claude-3-5-haiku-latest", "anthropic"),
    "sonnet": ("claude-3-7-sonnet-latest", "anthropic"),
    "opus": ("claude-3-opus-20240229", "anthropic"),
    # OpenAI models
    "gpt-4-1-mini": ("gpt-4.1-mini", "openai"),
    "gpt-4o-mini": ("gpt-4o-mini", "openai"),
    "gpt-4.1": ("gpt-4.1-2025-04-14", "openai"),
    "gpt-4-turbo": ("gpt-4-turbo-preview", "openai"),
    "gpt-3.5": ("gpt-3.5-turbo", "openai"),
}

# Also support full model names
MODEL_MAPPINGS.update(
    {
        # Anthropic full names
        "claude-3-5-haiku-latest": ("claude-3-5-haiku-latest", "anthropic"),
        "claude-3-7-sonnet-latest": ("claude-3-7-sonnet-latest", "anthropic"),
        "claude-3-opus-20240229": ("claude-3-opus-20240229", "anthropic"),
        # OpenAI full names
        "gpt-4.1-mini": ("gpt-4.1-mini", "openai"),
        "gpt-4o-mini": ("gpt-4o-mini", "openai"),
        "gpt-4.1-2025-04-14": ("gpt-4.1-2025-04-14", "openai"),
        "gpt-4-turbo-preview": ("gpt-4-turbo-preview", "openai"),
        "gpt-3.5-turbo": ("gpt-3.5-turbo", "openai"),
    }
)


def get_model_info(model_name: str) -> Tuple[str, Literal["openai", "anthropic"]]:
    """Get the full model name and provider for a given model name.

    Args:
        model_name: Short or full model name

    Returns:
        Tuple of (full_model_name, provider)

    Raises:
        ValueError: If the model name is not recognized
    """
    if model_name not in MODEL_MAPPINGS:
        valid_models = sorted(MODEL_MAPPINGS.keys())
        raise ValueError(
            f"Invalid model name: {model_name}. Must be one of: {', '.join(valid_models)}"
        )
    return MODEL_MAPPINGS[model_name]


def generate_test_batch(
    generator_type: str,
    num_companies: int,
    model: str = "gpt-4-turbo",
    output_dir: str = "data/synthetic/test_batches",
) -> str:
    """Generate a test batch using the specified generator.

    Args:
        generator_type: One of "random", "llm", or "hybrid"
        num_companies: Number of companies to generate
        model: Model name (short or full)
        output_dir: Directory to save the generated data

    Returns:
        Path to the generated CSV file
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get full model name and provider
    full_model_name, provider = get_model_info(model)

    # Initialize generator
    config = CompanyGenerationConfig()
    if generator_type == "random":
        generator = RandomCompanyGenerator(config=config)
    elif generator_type == "llm":
        generator = LLMCompanyGenerator(
            config=config, model=full_model_name, provider=provider
        )
    else:  # hybrid
        generator = HybridCompanyGenerator(
            config=config, model=full_model_name, provider=provider
        )

    # Generate companies
    print(f"\nGenerating {num_companies} companies using {generator_type} generator...")
    companies = generator.generate_companies(num_companies)

    # Save to CSV
    output_file = os.path.join(
        output_dir,
        f"{generator_type}_{provider}_{full_model_name.replace('.', '_')}_test_batch.csv",
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
        "--model",
        default="gpt-4-turbo",
        help="Model to use. Can be short name (e.g., 'haiku', 'sonnet', 'gpt-4.1') or full name.",
    )
    args = parser.parse_args()

    # Get model info
    try:
        full_model_name, provider = get_model_info(args.model)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate test batches
    results = {}
    for generator_type in ["random", "llm", "hybrid"]:
        try:
            output_file = generate_test_batch(
                generator_type,
                args.num_companies,
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
        f"generator_comparison_{provider}_{full_model_name.replace('.', '_')}.json",
    )
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\nGenerator Comparison Results:")
    print("=" * 50)
    print(f"Provider: {provider}")
    print(f"Model: {full_model_name}")
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
