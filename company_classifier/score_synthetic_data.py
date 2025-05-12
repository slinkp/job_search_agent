#!/usr/bin/env python3

"""
Score the realism and variety of synthetic company data.
This script helps evaluate different synthetic data generators by comparing
their output against real-world patterns and diversity metrics.
"""

import argparse
import csv
import json
from collections import Counter
from typing import Dict, List

from company_classifier.synthetic_data import CompanyType, FitCategory


def calculate_diversity_score(companies: List[Dict]) -> Dict[str, float]:
    """Calculate diversity scores for different aspects of the companies.

    Returns a dictionary of scores between 0 and 1, where 1 is maximum diversity.
    """
    scores = {}

    # 1. Company type distribution
    type_counts = Counter(c["type"] for c in companies)
    expected_types = {t.value for t in CompanyType}
    type_diversity = len(type_counts) / len(expected_types)
    scores["type_diversity"] = type_diversity

    # 2. Compensation range
    total_comps = [c["total_comp"] for c in companies]
    comp_range = max(total_comps) - min(total_comps)
    # Score based on range relative to expected range (160k-600k)
    comp_diversity = min(1.0, comp_range / 440000)  # 600k - 160k = 440k
    scores["compensation_diversity"] = comp_diversity

    # 3. Remote policy diversity
    remote_policies = [c["remote_policy"] for c in companies]
    unique_policies = len(set(remote_policies))
    # Score based on number of unique policies (expect at least 3)
    remote_diversity = min(1.0, unique_policies / 3)
    scores["remote_policy_diversity"] = remote_diversity

    # 4. Fit category distribution
    fit_counts = Counter(c["fit_category"] for c in companies)
    expected_categories = {fc.value for fc in FitCategory}
    fit_diversity = len(fit_counts) / len(expected_categories)
    scores["fit_category_diversity"] = fit_diversity

    # 5. Location diversity
    locations = [c["ny_address"] for c in companies if c["ny_address"]]
    location_diversity = min(
        1.0, len(set(locations)) / 5
    )  # Expect at least 5 unique locations
    scores["location_diversity"] = location_diversity

    # 6. Realistic relationships score
    relationship_score = 0.0
    valid_relationships = 0

    for company in companies:
        # Check RSU rules
        if company["type"] in ["private", "private finance"]:
            if company["rsu"] == 0:
                relationship_score += 1
            valid_relationships += 1

        # Check bonus rules for finance companies
        if company["type"] == "private finance":
            if company["bonus"] >= 50000:
                relationship_score += 1
            valid_relationships += 1

        # Check total size vs eng size
        if company["eng_size"] is not None and company["total_size"] is not None:
            if company["total_size"] >= company["eng_size"]:
                relationship_score += 1
            valid_relationships += 1

        # Check total comp calculation
        if (
            abs(
                company["total_comp"]
                - (company["base"] + company["rsu"] + company["bonus"])
            )
            < 1000
        ):
            relationship_score += 1
        valid_relationships += 1

    scores["realistic_relationships"] = (
        relationship_score / valid_relationships if valid_relationships > 0 else 0
    )

    # Calculate overall score as average of individual scores
    scores["overall_diversity"] = sum(scores.values()) / len(scores)

    return scores


def main():
    parser = argparse.ArgumentParser(
        description="Score the realism and variety of synthetic company data"
    )
    parser.add_argument(
        "input_file",
        help="Path to CSV file containing synthetic company data",
    )
    parser.add_argument(
        "--output",
        help="Path to save JSON output with scores (default: print to stdout)",
    )
    args = parser.parse_args()

    # Read companies from CSV
    companies = []
    with open(args.input_file, "r") as f:
        reader = csv.DictReader(f)
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

    # Calculate scores
    scores = calculate_diversity_score(companies)

    # Output results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(scores, f, indent=2)
    else:
        print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
