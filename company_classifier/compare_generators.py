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
from typing import Dict, List, Literal, Tuple

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


def process_companies_file(file_path: str) -> List[Dict]:
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
        default=["gpt-4-turbo"],
        help="Models to use. Can be short names (e.g., 'haiku', 'sonnet', 'gpt-4.1') or full names.",
    )
    parser.add_argument(
        "--generator",
        choices=["random", "llm", "hybrid", "all"],
        default="all",
        help="Which generator to run. Use 'all' to run all generators.",
    )
    args = parser.parse_args()

    # Validate all models first
    model_infos = {}
    for model in args.models:
        try:
            full_model_name, provider = get_model_info(model)
            model_infos[model] = (full_model_name, provider)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
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
        full_model_name, provider = model_infos[model]
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
            for metric, score in result["scores"].items():
                print(f"    {metric}: {score:.2f}")

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
                for metric, score in result["scores"].items():
                    print(f"    {metric}: {score:.2f}")

    print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    main()
