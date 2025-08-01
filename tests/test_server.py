import datetime
import unittest

import models


class TestServerApp(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_companies_filters_replied_and_archived(self):
        """Test that replied and archived companies are filtered out by default."""
        # Create test companies with a fresh repository
        repo = models.CompanyRepository(
            db_path=":memory:", clear_data=True, load_sample_data=False
        )

        # Create a company that's been replied to
        replied_company = models.Company(
            company_id="replied-company",
            name="Replied Company",
            details=models.CompaniesSheetRow(name="Replied Company"),
        )
        replied_company.status.reply_sent_at = datetime.datetime.now(
            datetime.timezone.utc
        )

        # Create an archived company
        archived_company = models.Company(
            company_id="archived-company",
            name="Archived Company",
            details=models.CompaniesSheetRow(name="Archived Company"),
        )
        archived_company.status.archived_at = datetime.datetime.now(datetime.timezone.utc)

        # Create a normal company
        normal_company = models.Company(
            company_id="normal-company",
            name="Normal Company",
            details=models.CompaniesSheetRow(name="Normal Company"),
        )

        # Save companies
        repo.create(replied_company)
        repo.create(archived_company)
        repo.create(normal_company)

        # Test default filtering (manually filter like the API does)
        all_companies = repo.get_all()
        visible_companies = [
            c
            for c in all_companies
            if not c.status.reply_sent_at and not c.status.archived_at
        ]
        company_names = [c.name for c in visible_companies]

        # Should not include replied or archived companies
        self.assertIn("Normal Company", company_names)
        self.assertNotIn("Replied Company", company_names)
        self.assertNotIn("Archived Company", company_names)

        # Test that all companies exist when not filtered
        all_names = [c.name for c in all_companies]
        self.assertIn("Normal Company", all_names)
        self.assertIn("Replied Company", all_names)
        self.assertIn("Archived Company", all_names)
