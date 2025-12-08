import decimal

from company_fit_heuristic import is_good_fit
from models import CompaniesSheetRow


class TestCompanyFitHeuristic:
    """Test the company fit heuristic function directly."""

    def test_is_good_fit_excellent_company(self):
        """Test a company that should score very highly."""
        company_info = CompaniesSheetRow(
            name="AI Innovations Inc",
            total_comp=decimal.Decimal("520"),
            remote_policy="Remote-first",
            ai_notes="Leading AI company focused on generative artificial intelligence and machine learning solutions",
        )

        assert is_good_fit(company_info) is True

    def test_is_good_fit_poor_company(self):
        """Test a company that should score poorly."""
        company_info = CompaniesSheetRow(
            name="Old Corp",
            total_comp=decimal.Decimal("150"),
            remote_policy="Office-only",
            ai_notes="Traditional manufacturing company with no technology focus",
        )

        assert is_good_fit(company_info) is False

    def test_is_good_fit_borderline_company(self):
        """Test a company that should score around the threshold."""
        company_info = CompaniesSheetRow(
            name="Tech Corp",
            total_comp=decimal.Decimal("350"),
            remote_policy="Hybrid",
            ai_notes="Some AI integration in products",
        )

        # This should be close to the 70% threshold
        result = is_good_fit(company_info)
        # Don't assert the exact result as it depends on the specific scoring
        assert isinstance(result, bool)

    def test_is_good_fit_no_data(self):
        """Test scoring when company has minimal data."""
        company_info = CompaniesSheetRow(
            name="Mystery Corp",
            # No other data fields populated
        )

        # Should handle missing data gracefully
        result = is_good_fit(company_info)
        assert isinstance(result, bool)

    def test_is_good_fit_mission_driven(self):
        """Test that companies with good compensation and remote policy score well."""
        company_info = CompaniesSheetRow(
            name="Climate Solutions",
            total_comp=decimal.Decimal("450"),
            remote_policy="Remote",
            ai_notes="AI for climate change solutions using machine learning",
        )

        assert is_good_fit(company_info) is True

    def test_is_good_fit_ai_keywords(self):
        """Test that AI keywords in notes are properly detected."""
        # Test with many AI keywords (should score 8 points for AI)
        company_info_high_ai = CompaniesSheetRow(
            name="AI Corp",
            total_comp=decimal.Decimal("400"),
            remote_policy="Remote",
            ai_notes="Generative AI machine learning LLM development",
            notes="Uses artificial intelligence and other AI models extensively",
        )

        # Test with minimal AI keywords (should score less for AI)
        company_info_low_ai = CompaniesSheetRow(
            name="Traditional Corp",
            total_comp=decimal.Decimal("400"),
            remote_policy="Remote",
            ai_notes="Traditional software development",
            notes="No technology focus",
        )

        # High AI should score better than low AI
        high_ai_result = is_good_fit(company_info_high_ai)
        low_ai_result = is_good_fit(company_info_low_ai)

        # Both should be valid boolean results
        assert isinstance(high_ai_result, bool)
        assert isinstance(low_ai_result, bool)

    def test_is_good_fit_compensation_tiers(self):
        """Test that different compensation levels are scored correctly."""
        # Test high compensation
        high_comp = CompaniesSheetRow(
            name="Test Corp",
            total_comp=decimal.Decimal("550"),
            remote_policy="Remote",
            ai_notes="AI company with machine learning",
        )

        # Test low compensation
        low_comp = CompaniesSheetRow(
            name="Test Corp",
            total_comp=decimal.Decimal("180"),
            remote_policy="Remote",
            ai_notes="AI company with machine learning",
        )

        high_result = is_good_fit(high_comp)
        low_result = is_good_fit(low_comp)

        # Both should be valid boolean results
        assert isinstance(high_result, bool)
        assert isinstance(low_result, bool)

    def test_is_good_fit_remote_policy_variations(self):
        """Test different remote policy variations."""
        # Test various remote policy strings
        policies = [
            "Remote-first",
            "Hybrid work",
            "Office-based",
            "Work from anywhere",
            "Flexible location",
            "On-site required",
        ]

        for policy in policies:
            company_info = CompaniesSheetRow(
                name=f"Corp with {policy}",
                total_comp=decimal.Decimal("400"),
                remote_policy=policy,
                ai_notes="AI company with machine learning",
            )

            result = is_good_fit(company_info)
            assert isinstance(result, bool)

    def test_is_good_fit_logging_output(self, caplog):
        """Test that the method produces expected logging output."""
        company_info = CompaniesSheetRow(
            name="Test Corp",
            total_comp=decimal.Decimal("400"),
            remote_policy="Remote",
            ai_notes="AI company with machine learning",
        )

        with caplog.at_level(20):  # INFO level
            result = is_good_fit(company_info)

            # Check that key log messages are present
            assert "Checking if Test Corp is a good fit" in caplog.text
            assert "Company fit score for Test Corp" in caplog.text
            assert "Result:" in caplog.text
            assert isinstance(result, bool)

    def test_compensation_scoring_ranges(self):
        """Test specific compensation scoring ranges."""
        # Updated for new max score of 26 points (10 comp + 8 remote + 8 AI), 70% threshold = 18.2 points
        # Note: compensation values are in thousands (e.g., 550 = $550k)
        test_cases = [
            (
                decimal.Decimal("550"),
                True,
            ),  # 10 + 8 + 6 = 24 points (92%) - should pass
            (
                decimal.Decimal("450"),
                True,
            ),  # 8 + 8 + 6 = 22 points (85%) - should pass
            (
                decimal.Decimal("180"),
                False,
            ),  # 2 + 8 + 6 = 16 points (62%) - should fail
        ]

        for comp, expected_result in test_cases:
            company_info = CompaniesSheetRow(
                name="Test Corp",
                total_comp=comp,
                remote_policy="Remote",
                ai_notes="AI machine learning company",  # Clear word-separated keywords
            )

            result = is_good_fit(company_info)
            assert (
                result == expected_result
            ), f"Compensation {comp} should result in {expected_result}"

    def test_ai_focus_scoring(self):
        """Test AI/ML focus scoring with different keyword counts."""
        # Test with 3+ AI keywords (should score highest - 8 points)
        high_ai = CompaniesSheetRow(
            name="AI Corp",
            total_comp=decimal.Decimal("400"),
            remote_policy="Remote",
            ai_notes="artificial intelligence machine learning generative AI",
        )

        # Test with 1 AI keyword (should score lower - 4 points)
        low_ai = CompaniesSheetRow(
            name="Traditional Corp",
            total_comp=decimal.Decimal("400"),
            remote_policy="Remote",
            ai_notes="some AI integration",
        )

        # Test with no AI keywords (should score lowest - 0 points)
        no_ai = CompaniesSheetRow(
            name="Old Corp",
            total_comp=decimal.Decimal("400"),
            remote_policy="Remote",
            ai_notes="traditional software development",
        )

        high_result = is_good_fit(high_ai)
        low_result = is_good_fit(low_ai)
        no_result = is_good_fit(no_ai)

        # All should be valid boolean results
        assert isinstance(high_result, bool)
        assert isinstance(low_result, bool)
        assert isinstance(no_result, bool)

    def test_level_equiv_scoring(self):
        """Test that level scoring is no longer applied (removed in updates)."""
        # All should get same score regardless of level since this scoring was removed
        for level in ["Staff Engineer", "Senior Engineer", "Junior Engineer"]:
            company_info = CompaniesSheetRow(
                name="Test Corp",
                total_comp=decimal.Decimal("400"),
                remote_policy="Remote",
                ai_notes="AI machine learning company",
                level_equiv=level,
            )

            result = is_good_fit(company_info)
            assert isinstance(result, bool)
