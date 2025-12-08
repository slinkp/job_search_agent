"""
Company fit heuristic for evaluating whether a company is a good match.

Based on the Ideal Work Vision 2025 criteria, this module provides
a scoring system to evaluate companies on multiple dimensions.
"""

import logging

from models import CompaniesSheetRow

logger = logging.getLogger(__name__)


def is_good_fit(company_info: CompaniesSheetRow) -> bool:
    """
    Evaluate if a company is a good fit based on the Ideal Work Vision criteria.

    Uses a scoring system where each criterion contributes points.
    Returns True if the total score meets the threshold.

    Args:
        company_info: Company data from the spreadsheet

    Returns:
        bool: True if the company is a good fit, False otherwise
    """
    logger.info(f"Checking if {company_info.name} is a good fit...")

    score = 0
    max_score = 0
    reasons = []

    # 1. Compensation - Target $500k total comp
    # Note: compensation values are stored in thousands (e.g., 500 for $500k)
    max_score += 10
    if company_info.total_comp:
        if company_info.total_comp >= 500:
            score += 10
            reasons.append("Excellent compensation (≥$500k)")
        elif company_info.total_comp >= 400:
            score += 8
            reasons.append("Very good compensation (≥$400k)")
        elif company_info.total_comp >= 325:
            score += 5
            reasons.append("Good compensation (≥$300k)")
        else:
            score += 2
            reasons.append("Below target compensation")
    else:
        # No compensation data - neutral
        score += 5
        reasons.append("No compensation data available")

    # 2. Remote Policy - Location flexibility is important
    max_score += 8
    if company_info.remote_policy:
        remote_policy_lower = company_info.remote_policy.lower()
        if (
            "hybrid" in remote_policy_lower
            or "remote" in remote_policy_lower
            or "flexible" in remote_policy_lower
            or "anywhere" in remote_policy_lower
        ):
            score += 8
            reasons.append(
                f"Remote policy {remote_policy_lower} promising"
            )  # _Hybrid/flexible policy")
        elif "office" in remote_policy_lower or "on-site" in remote_policy_lower:
            score += 2
            reasons.append(f"Office-based policy: {remote_policy_lower} ")
            # TODO: subtract 50 points if required to be in a non-NYC office.
            # That's maybe not clear in the data yet?
        else:
            score += 0
            reasons.append(f"Unclear remote policy: {company_info.remote_policy}")
    else:
        score += 0
        reasons.append("No remote policy information")

    # 3. AI/ML Focus - Should be working with generative AI/ML
    max_score += 8
    ai_keywords = [
        "ai",
        "artificial intelligence",
        "machine learning",
        "ml",
        "generative",
        "llm",
    ]
    ai_content = (
        f"{company_info.ai_notes or ''} {company_info.notes or ''}".lower().split()
    )

    ai_mentions = sum(1 for keyword in ai_keywords if keyword in ai_content)
    if ai_mentions >= 3:
        score += 8
        reasons.append("Strong AI/ML focus")
    elif ai_mentions >= 2:
        score += 6
        reasons.append("Good AI/ML presence")
    elif ai_mentions >= 1:
        score += 4
        reasons.append("Some AI/ML involvement")
    elif ai_mentions == 0:
        score += 0
        reasons.append(f"Unclear AI/ML focus: {ai_content}")

    # Role Level - Prefer staff or senior roles
    # TODO: Role-specific data is not in the company model yet.

    # Company Type - Prefer mission-driven types
    # TODO: We don't have mission information yet.

    # Calculate final score as percentage
    final_score = (score / max_score) * 100 if max_score > 0 else 0

    # Threshold for "good fit" - 70% or higher
    is_fit = final_score >= 70

    logger.info(
        f"Company fit score for {company_info.name}: {final_score:.1f}% ({score}/{max_score})"
    )
    logger.info(f"Reasons: {', '.join(reasons)}")
    logger.info(f"Result: {'GOOD FIT' if is_fit else 'NOT A FIT'}")

    return is_fit
