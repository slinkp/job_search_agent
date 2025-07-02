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
    # Anthropic models, cheapest to most expensive.
    # None of these are deprecated as of 2025-07-01.
    "haiku-3": ("claude-3-haiku-20240307", "anthropic"),  # $0.25
    "haiku-3.5": ("claude-3-5-haiku-20241022", "anthropic"),  # $0.80
    # Sonnet 3.5, 3.7 and 4.0 are same cost.
    "sonnet-3.5": ("claude-3-5-sonnet-20241022", "anthropic"),  # $3.00
    "sonnet-3.7": ("claude-3-7-sonnet-20250219", "anthropic"),  # $3.00
    "sonnet-4": ("claude-sonnet-4-20250514", "anthropic"),  # $3.00
    # Opus is WAY more expensive than Sonnet.
    "opus-4": ("claude-opus-4-20250514", "anthropic"),  # $15.00 !!!
    ############################################################
    # OpenAI models, cheapest to most expensive.
    "gpt-4.1-nano": ("gpt-4.1-nano-2025-04-14", "openai"),  # $0.10
    "gpt-4o-mini": ("gpt-4o-mini-2024-07-18", "openai"),  # $0.15
    "gpt-4.1-mini": ("gpt-4.1-mini-2025-04-14", "openai"),  # $0.40
    "o4-mini": ("o4-mini-2025-04-16", "openai"),  # $1.10
    "gpt-4.1": ("gpt-4.1-2025-04-14", "openai"),  # $2.00
    # "o3": ("o3-2025-04-16", "openai"),  # $2.00 - requires biometric auth, no thanks
    "gpt-4-turbo": ("gpt-4-turbo-2024-04-09", "openai"),  # $10.00 !!!
}

# Also support full model names, and dashes
ALL_MODEL_MAPPINGS = {}
for shortname, (fullname, provider) in MODEL_MAPPINGS.items():
    ALL_MODEL_MAPPINGS[shortname] = (fullname, provider)
    ALL_MODEL_MAPPINGS[fullname] = (fullname, provider)
    ALL_MODEL_MAPPINGS[shortname.replace("-", ".")] = (fullname, provider)
    ALL_MODEL_MAPPINGS[shortname.replace(".", "-")] = (fullname, provider)


def get_model_info(model_name: str) -> Tuple[str, Literal["openai", "anthropic"]]:
    """Get the full model name and provider for a given model name.

    Args:
        model_name: Short or full model name

    Returns:
        Tuple of (full_model_name, provider)

    Raises:
        ValueError: If the model name is not recognized
    """
    if model_name not in ALL_MODEL_MAPPINGS:
        valid_models = sorted(ALL_MODEL_MAPPINGS.keys())
        raise ValueError(
            f"Invalid model name: {model_name}. Must be one of: {', '.join(valid_models)}"
        )
    return ALL_MODEL_MAPPINGS[model_name]


def generate_test_batch(
    generator_type: str,
    num_companies: int,
    model: str = "gpt-4-turbo",
    output_dir: str = "data/synthetic/test_batches",
    batch_size: int = 5,
) -> str:
    """Generate a test batch using the specified generator.

    Args:
        generator_type: One of "random", "llm", or "hybrid"
        num_companies: Number of companies to generate
        model: Model name (short or full)
        output_dir: Directory to save the generated data
        batch_size: Batch size for LLM generators (ignored for random generator)

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
            config=config, model=full_model_name, provider=provider, batch_size=batch_size
        )
    else:  # hybrid
        generator = HybridCompanyGenerator(
            config=config, model=full_model_name, provider=provider, batch_size=batch_size
        )

    # Generate companies
    print(f"\nGenerating {num_companies} companies using {generator_type} generator...")
    if generator_type != "random":
        expected_api_calls = (num_companies + batch_size - 1) // batch_size
        print(f"Expected API calls with batch_size={batch_size}: {expected_api_calls}")

    companies = generator.generate_companies(num_companies)

    # Save to CSV
    output_file = os.path.join(
        output_dir,
        f"{generator_type}_{provider}_{full_model_name.replace('.', '_')}_batch{batch_size}_test_batch.csv",
    )
    save_companies_to_csv(companies, output_file)

    return output_file


def process_companies_file(file_path: str) -> list[Dict]:
    """Process a CSV file of companies and return the data with proper types.

    Args:
        file_path: Path to the CSV file

    Returns:
        List of company dictionaries with proper numeric types
    """
    with open(file_path, "r") as f:
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
                if row[field] is not None and row[field].isnumeric():
                    row[field] = float(row[field])
                else:
                    row[field] = None
            companies.append(row)
    return companies


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
        "--models",
        nargs="+",
        default=["gpt-4.1-mini"],
        help="Models to use. Can be short names (e.g., 'haiku', 'sonnet', 'gpt-4.1') or full names."
        " Use 'all' to run all models.",
    )
    parser.add_argument(
        "--generator",
        choices=["random", "llm", "hybrid", "all"],
        default="all",
        help="Which generator to run. Use 'all' to run all generators.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Batch size for LLM generators (1-20). Higher values make fewer API calls but may be less robust.",
    )
    args = parser.parse_args()

    # Validate batch size
    if not (1 <= args.batch_size <= 20):
        print("Error: --batch-size must be between 1 and 20", file=sys.stderr)
        sys.exit(1)

    # Validate all models first
    if "all" in args.models:
        # Get all full names, no duplicates
        args.models = list(set(v[0] for v in ALL_MODEL_MAPPINGS.values()))

    have_invalid_models = False
    for model in args.models:
        try:
            full_model_name, provider = get_model_info(model)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            have_invalid_models = True
    if have_invalid_models:
        sys.exit(1)

    # Initialize results structure
    all_results = {
        "generators": {},  # For random generator results
        "models": {},  # For model-specific results (llm and hybrid)
    }
    generator_types = (
        ["random", "llm", "hybrid"] if args.generator == "all" else [args.generator]
    )

    # Run random generator once if needed
    if "random" in generator_types:
        try:
            output_file = generate_test_batch(
                "random",
                args.num_companies,
                output_dir=args.output_dir,
                batch_size=args.batch_size,
            )
            companies = process_companies_file(output_file)
            scores = calculate_diversity_score(companies)
            all_results["generators"]["random"] = {
                "scores": scores,
                "output_file": output_file,
            }
        except Exception as e:
            print(f"Error generating random test batch: {e}", file=sys.stderr)
            all_results["generators"]["random"] = {
                "error": str(e),
            }

    # Run LLM-dependent generators for each model
    for model in args.models:
        full_model_name, provider = get_model_info(model)
        print(f"\nProcessing model: {full_model_name} ({provider})")
        print("=" * 50)

        model_results = {}
        # Run LLM-dependent generators
        for generator_type in [g for g in generator_types if g != "random"]:
            try:
                output_file = generate_test_batch(
                    generator_type,
                    args.num_companies,
                    model=model,
                    output_dir=args.output_dir,
                    batch_size=args.batch_size,
                )

                # Calculate scores
                companies = process_companies_file(output_file)
                scores = calculate_diversity_score(companies)
                model_results[generator_type] = {
                    "scores": scores,
                    "output_file": output_file,
                }

            except Exception as e:
                print(
                    f"Error generating {generator_type} test batch: {e}", file=sys.stderr
                )
                model_results[generator_type] = {
                    "error": str(e),
                }

        all_results["models"][model] = {
            "full_name": full_model_name,
            "provider": provider,
            "results": model_results,
        }

    # Save comparison results
    results_file = os.path.join(
        args.output_dir,
        "generator_comparison_results.json",
    )
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)

    # Print summary
    print("\nGenerator Comparison Results:")
    print("=" * 50)

    # Print random generator results if any
    if "random" in all_results["generators"]:
        print("\nRANDOM Generator:")
        print("-" * 50)
        result = all_results["generators"]["random"]
        if "error" in result:
            print(f"  Error: {result['error']}")
        else:
            print(f"  Output file: {result['output_file']}")
            print("  Scores:")
            scores = result["scores"]
            if isinstance(scores, dict):
                for metric, score in scores.items():
                    print(f"    {metric}: {score:.2f}")
            else:
                print(f"    Error: Invalid scores format: {scores}")

    # Print model-specific results
    for model, model_data in all_results["models"].items():
        print(f"\nModel: {model_data['full_name']} ({model_data['provider']})")
        print("-" * 50)
        for generator_type, result in model_data["results"].items():
            print(f"\n{generator_type.upper()} Generator:")
            if "error" in result:
                print(f"  Error: {result['error']}")
            else:
                print(f"  Output file: {result['output_file']}")
                print("  Scores:")
                scores = result["scores"]
                if isinstance(scores, dict):
                    for metric, score in scores.items():
                        print(f"    {metric}: {score:.2f}")
                else:
                    print(f"    Error: Invalid scores format: {scores}")

    print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    main()
