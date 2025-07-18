#!/usr/bin/env python3

import argparse
import decimal
import logging

from libjobsearch import upsert_company_in_spreadsheet
from models import CompaniesSheetRow, CompanyRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def normalize_compensation(update_sheet: bool = False, sheet_type: str = "prod") -> None:
    """
    Normalize compensation data in the database according to the following heuristic:
    - If above 1000, assume it's in dollars and leave alone
    - If less than 1000, assume it's in thousands and multiply by 1000

    Args:
        update_sheet: Whether to update the Google Sheet with normalized values
        sheet_type: Which sheet to update ("test" or "prod")
    """
    repo = CompanyRepository()
    companies = repo.get_all()
    normalized_count = 0
    sheet_update_count = 0

    for company in companies:
        details = company.details
        needs_update = False

        # Helper function to normalize a compensation value
        def normalize_value(value):
            if value is None:
                return None
            if value < 1000:
                return value * 1000
            return value

        # Check and normalize total_comp
        if details.total_comp is not None:
            new_total_comp = normalize_value(details.total_comp)
            if new_total_comp != details.total_comp:
                details.total_comp = decimal.Decimal(str(new_total_comp))
                needs_update = True

        if details.base is not None:
            new_base = normalize_value(details.base)
            if new_base != details.base:
                details.base = decimal.Decimal(str(new_base))
                needs_update = True

        # Check and normalize RSU
        if details.rsu is not None:
            new_rsu = normalize_value(details.rsu)
            if new_rsu != details.rsu:
                details.rsu = decimal.Decimal(str(new_rsu))
                needs_update = True

        # Check and normalize bonus
        if details.bonus is not None:
            new_bonus = normalize_value(details.bonus)
            if new_bonus != details.bonus:
                details.bonus = decimal.Decimal(str(new_bonus))
                needs_update = True

        if details.total_comp is None:
            total_comp = (details.base or 0) + (details.rsu or 0) + (details.bonus or 0)
            if total_comp != 0:
                print(f"Filled in missing total_comp for {company.name}")
                details.total_comp = decimal.Decimal(str(total_comp))
                needs_update = True

        # Update the database if any values were normalized
        if needs_update:
            company.details = details
            repo.update(company)
            normalized_count += 1
            print(f"Normalized compensation for {company.name}")

        # Update Google Sheet if requested, for any company with compensation data
        if update_sheet and any(
            [details.total_comp, details.base, details.rsu, details.bonus]
        ):
            # Create a minimal sheet row with just the compensation fields
            sheet_row = CompaniesSheetRow(
                name=company.name,
                total_comp=details.total_comp,
                base=details.base,
                rsu=details.rsu,
                bonus=details.bonus,
            )
            args = argparse.Namespace(sheet=sheet_type)
            upsert_company_in_spreadsheet(sheet_row, args)
            sheet_update_count += 1
            print(f"Updated Google Sheet compensation for {company.name}")

    print("\nNormalization complete:")
    print(f"- Normalized {normalized_count} companies in database")
    if update_sheet:
        print(f"- Updated {sheet_update_count} companies in Google Sheet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize compensation data in the database and optionally update Google Sheet"
    )
    parser.add_argument(
        "--update-sheet",
        action="store_true",
        help="Update compensation data in Google Sheet for all companies with compensation info",
    )
    parser.add_argument(
        "--sheet",
        choices=["test", "prod"],
        default="prod",
        help="Which sheet to update (default: prod)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    normalize_compensation(update_sheet=args.update_sheet, sheet_type=args.sheet)
