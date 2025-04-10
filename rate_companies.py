#!/usr/bin/env python3

import csv
import datetime
from typing import List, Optional

from models import Company, CompanyRepository, FitCategory, company_repository


def format_company_info(company: Company) -> str:
    """Format company information for display to the user."""
    details = company.details
    status = company.status

    info = [
        f"\nCompany: {company.name}",
        f"Type: {details.type or 'Unknown'}",
        f"Total Compensation: ${details.total_comp or 'Unknown'}",
        f"Base Salary: ${details.base or 'Unknown'}",
        f"RSU: ${details.rsu or 'Unknown'}",
        f"Bonus: ${details.bonus or 'Unknown'}",
        f"Remote Policy: {details.remote_policy or 'Unknown'}",
        f"Engineering Size: {details.eng_size or 'Unknown'}",
        f"Total Size: {details.total_size or 'Unknown'}",
        f"NY Address: {details.ny_address or 'Unknown'}",
        f"AI Notes: {details.ai_notes or 'None'}",
        "",
        "Current Fit Decision:",
        f"Category: {status.fit_category.value if status.fit_category else 'Not rated'}",
        f"Confidence: {status.fit_confidence_score or 'N/A'}",
    ]
    return "\n".join(info)


def get_user_rating() -> Optional[FitCategory]:
    """Get rating input from user."""
    print("\nRate this company:")
    print("1. Good fit")
    print("2. Bad fit")
    print("3. Need more information")
    print("q. Quit")

    while True:
        choice = input("\nEnter your choice (1/2/3/q): ").strip().lower()
        if choice == "q":
            return None
        if choice == "1":
            return FitCategory.GOOD
        if choice == "2":
            return FitCategory.BAD
        if choice == "3":
            return FitCategory.NEEDS_MORE_INFO
        print("Invalid choice. Please try again.")


def save_ratings_to_csv(companies: List[Company], filename: str):
    """Save the ratings to a CSV file for model training."""
    with open(filename, "w", newline="") as f:
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
                    company.company_id,
                    company.name,
                    company.details.type,
                    company.details.valuation,
                    company.details.total_comp,
                    company.details.base,
                    company.details.rsu,
                    company.details.bonus,
                    company.details.remote_policy,
                    company.details.eng_size,
                    company.details.total_size,
                    company.details.headquarters,
                    company.details.ny_address,
                    company.details.ai_notes,
                    (
                        company.status.fit_category.value
                        if company.status.fit_category
                        else None
                    ),
                    company.status.fit_confidence_score,
                ]
            )


def rate_companies(
    repo: CompanyRepository,
    output_file: str,
    confidence: float = 0.8,
    rerate: bool = False,
):
    """Rate companies and save the results.

    Args:
        repo: The company repository to use
        output_file: Path to save the CSV output
        confidence: Confidence score to assign to manual ratings (0.0-1.0)
        rerate: If True, only show previously rated companies. If False, only show unrated companies.
    """
    companies = repo.get_all()
    rated_companies = []

    # Filter companies based on mode
    companies_to_rate = [
        c
        for c in companies
        if bool(c.status.fit_category)
        == rerate  # Show rated in rerate mode, unrated in normal mode
    ]

    if not companies_to_rate:
        print("\nNo companies found to rate.")
        if rerate:
            print("There are no previously rated companies.")
        else:
            print(
                "All companies have already been rated. Use --rerate to re-rate companies."
            )
        return

    print(f"\nFound {len(companies_to_rate)} companies to rate.")
    if rerate:
        print("Re-rating previously rated companies.")
    else:
        print("Rating only unrated companies.")
    print("You will be shown company information and asked to rate each one.")
    print(
        "The ratings will be used to train a model for automatic company fit decisions."
    )

    try:
        for company in companies_to_rate:
            print("\n" + "=" * 80)
            print(format_company_info(company))

            rating = get_user_rating()
            if rating is None:  # User quit
                break

            # Update company status with the new rating
            company.status.fit_category = rating
            company.status.fit_confidence_score = confidence
            company.status.fit_decision_timestamp = datetime.datetime.now(
                datetime.timezone.utc
            )

            # Save to database
            repo.update(company)
            rated_companies.append(company)

            print(f"\nSaved rating for {company.name}")

    except KeyboardInterrupt:
        print("\nRating process interrupted.")

    if rated_companies:
        save_ratings_to_csv(rated_companies, output_file)
        print(f"\nSaved {len(rated_companies)} ratings to {output_file}")
    else:
        # Still create the file with headers even if no ratings
        save_ratings_to_csv([], output_file)
        print("\nNo ratings were collected.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Rate companies for ML training data")
    parser.add_argument(
        "--output",
        default="company_ratings.csv",
        help="Output CSV file for training data",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.8,
        help="Confidence score to assign to manual ratings (0.0-1.0)",
    )
    parser.add_argument(
        "--rerate",
        action="store_true",
        help="Re-rate previously rated companies instead of rating new ones",
    )
    args = parser.parse_args()

    repo = company_repository()
    rate_companies(repo, args.output, args.confidence, args.rerate)
