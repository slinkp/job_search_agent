import argparse
import datetime
import logging
import signal
import time
from typing import Optional

import libjobsearch
import models
import spreadsheet_client
from logsetup import setup_logging
from models import normalize_company_name
from spreadsheet_client import MainTabCompaniesClient
from tasks import TaskManager, TaskStatus, TaskType, task_manager

logger = logging.getLogger("research_daemon")


class TaskStatusContext:

    def __init__(self, task_mgr: TaskManager, task_id: str, task_type: TaskType):
        self.task_mgr = task_mgr
        self.task_id = task_id
        self.task_type = task_type

    def __enter__(self):
        self.task_mgr.update_task(self.task_id, TaskStatus.RUNNING)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.task_mgr.update_task(self.task_id, TaskStatus.COMPLETED)
        else:
            self.task_mgr.update_task(
                self.task_id, TaskStatus.FAILED, error=str(exc_value)
            )


class ResearchDaemon:

    def __init__(
        self, args: argparse.Namespace, cache_settings: libjobsearch.CacheSettings
    ):
        self.running = False
        self.task_mgr = task_manager()
        self.company_repo = models.company_repository()
        self.ai_model = args.model
        self.dry_run = args.dry_run
        self.headless = not getattr(args, "no_headless", False)
        if self.dry_run:
            logger.info("Running in DRY RUN mode - no emails will be sent")
        logger.info(
            f"Browser will run in {'headless' if self.headless else 'visible'} mode"
        )
        self.args = args
        self.jobsearch = libjobsearch.JobSearch(
            args, loglevel=logging.DEBUG, cache_settings=cache_settings
        )

    def start(self):
        self.running = True
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        logger.info("Research daemon starting")
        while self.running:
            try:
                self.process_next_task()
                time.sleep(1)  # Polling interval
            except Exception:
                logger.exception("Error processing task")
                time.sleep(5)  # Back off on errors

    def stop(self, signum=None, frame=None) -> int:
        logger.info("Research daemon stopping")
        self.running = False
        return 0

    def process_next_task(self):
        row = self.task_mgr.get_next_pending_task()

        if row:
            task_id, task_type, task_args = row
            logger.info(
                f"Processing task {task_id} of type {task_type} with args:\n{task_args}"
            )
            with TaskStatusContext(self.task_mgr, task_id, task_type):
                if task_type == TaskType.COMPANY_RESEARCH:
                    self.do_research(task_args)
                elif task_type == TaskType.GENERATE_REPLY:
                    self.do_generate_reply(task_args)
                elif task_type == TaskType.FIND_COMPANIES_FROM_RECRUITER_MESSAGES:
                    self.do_find_companies_in_recruiter_messages(task_args)
                elif task_type == TaskType.SEND_AND_ARCHIVE:
                    self.do_send_and_archive(task_args)
                elif task_type == TaskType.IGNORE_AND_ARCHIVE:
                    self.do_ignore_and_archive(task_args)
                elif task_type == TaskType.IMPORT_COMPANIES_FROM_SPREADSHEET:
                    self.do_import_companies_from_spreadsheet(task_args)
                else:
                    logger.error(f"Ignoring unsupported task type: {task_type}")
                logger.info(f"Task {task_id} completed")

    def _generate_company_id(self, name: str) -> str:
        """Generate a company ID from a name by normalizing it."""
        # Use the normalize_company_name function from models.py
        return normalize_company_name(name)

    def get_content_for_research(
        self,
        company: Optional[models.Company],
        company_name: Optional[str],
        company_url: Optional[str],
        content: Optional[str],
    ) -> dict[str, str]:

        content = (content or "").strip()
        company_name = (company_name or "").strip()
        company_url = (company_url or "").strip()
        if company:
            company_name = (company_name or company.name or "").strip()
            company_url = (company_url or company.details.url or "").strip()
            if not content and company.recruiter_message:
                content = (company.recruiter_message.message or "").strip()
                logger.info(f"Using existing initial message: {content[:400]}")

        # Augment content with company name and URL if available
        if company_url:
            content = f"Company URL: {company_url}\n\n{content}"
        if company_name:
            content = f"Company name: {company_name}\n\n{content}"

        content = content.strip()
        if not content:
            raise ValueError(
                f"No searchable found via any of content, name, url, or existing company"
            )
        return {
            "content": content,
            "company_name": company_name,
            "company_url": company_url,
        }

    def do_research(self, args: dict) -> Optional[models.Company]:
        # Extract args, with URL and name being optional
        company_id = args.get("company_id", "").strip()
        company_name = args.get("company_name", "").strip()
        company_url = args.get("company_url", "").strip()
        content = args.get("content", "").strip()

        # If we have a company_id, try to get the existing company
        existing = None
        if company_id:
            existing = self.company_repo.get(company_id)
        elif company_name:
            # If we have a company name, try to find an existing company with that name
            existing = self.company_repo.get_by_normalized_name(company_name)

        # Determine what content to use for research
        content_for_research = self.get_content_for_research(
            company=existing,
            company_name=company_name,
            company_url=company_url,
            content=content,
        )
        content = content_for_research["content"]
        if content is None:
            raise ValueError("No content for research")

        company_name = content_for_research["company_name"]
        company_url = content_for_research["company_url"]

        company = None
        try:
            # TODO: Pass more context from email, etc.
            # And anything we know about the company already?
            company = self.jobsearch.research_company(content, model=self.ai_model)

            # Log any research errors that occurred
            research_errors = company.status.research_errors
            if research_errors:
                logger.warning(f"Research completed with {len(research_errors)} errors:")
                for err in research_errors:
                    logger.warning(f"  - {err.step}: {err.error}")

            # Set up result_company (will be either existing or new)
            result_company = None

            if existing:
                # Update existing company with new research results
                logger.info(f"Updating company {company_name or existing.name}")
                existing.details = company.details
                existing.name = company.name or existing.name
                existing.status.research_errors = research_errors
                self.company_repo.update(existing)
                result_company = existing
            else:
                # Check for duplicates by normalized name
                normalized_match = self.company_repo.get_by_normalized_name(company.name)
                if normalized_match:
                    # Update the existing company found via normalized name
                    logger.info(
                        f"Found existing company with normalized name match: {normalized_match.name}"
                    )
                    normalized_match.details = company.details
                    normalized_match.name = company.name or normalized_match.name
                    normalized_match.status.research_errors = research_errors
                    self.company_repo.update(normalized_match)
                    result_company = normalized_match
                else:
                    # Create a new company
                    logger.info(f"Creating company {company.name}")
                    self.company_repo.create(company)
                    result_company = company

            # Update the spreadsheet with the researched company data - moved to end of try block
            libjobsearch.upsert_company_in_spreadsheet(result_company.details, self.args)

        except Exception as e:
            logger.exception(f"Error researching company {company_name or 'unknown'}")

            # If we already found an existing company by ID or normalized name, update it with the error
            if existing:
                # Record error in existing company
                error_message = f"Complete research failure: {str(e)}"
                existing.status.research_errors.append(
                    models.ResearchStepError(
                        step="research_company",
                        error=error_message,
                    )
                )
                existing.details.notes = (
                    existing.details.notes or ""
                ) + f"\nResearch failed: {str(e)}"
                self.company_repo.update(existing)

            # Create a minimal company record if no existing company was found
            # Use the same unknown company name logic as in libjobsearch.py
            # TODO: put this in a function and use both places.
            if not company_name:
                company_name = f"<UNKNOWN {int(time.time() * 1000 * 1000)}>"
                logger.warning(f"Company name not found, using {company_name}")

            minimal_row = models.CompaniesSheetRow(
                name=company_name,
                url=company_url or "",
                notes=f"Research failed: {str(e)}",
            )
            company_status = models.CompanyStatus(
                research_errors=[
                    models.ResearchStepError(
                        step="research_company",
                        error=f"Complete research failure: {str(e)}",
                    )
                ],
            )
            company = models.Company(
                company_id=company_id or self._generate_company_id(company_name),
                name=company_name,
                details=minimal_row,
                status=company_status,
            )

            # Check for duplicates by normalized name
            normalized_company = self.company_repo.get_by_normalized_name(company.name)
            if normalized_company:
                logger.info(
                    f"Found existing company with normalized name match: {normalized_company.name}"
                )
                normalized_company.details = company.details
                normalized_company.status = company.status
                self.company_repo.update(normalized_company)
                company = normalized_company
            else:
                self.company_repo.create(company)

            # Try to update the spreadsheet with minimal info
            try:
                libjobsearch.upsert_company_in_spreadsheet(company.details, self.args)
            except Exception as spreadsheet_error:
                logger.exception(f"Failed to update spreadsheet: {spreadsheet_error}")

            raise
        return existing or company

    def do_generate_reply(self, args: dict):
        # TODO: Use LLM to generate reply
        assert "company_id" in args
        company = self.company_repo.get(args["company_id"])
        assert company is not None
        assert company.recruiter_message is not None
        logger.info(f"Generating reply for {company.company_id}")
        # TODO: Include more company info context in reply args
        reply = self.jobsearch.generate_reply(company.initial_message)
        company.reply_message = reply
        self.company_repo.update(company)
        logger.info(f"Updated reply for {company.company_id}")

    def do_find_companies_in_recruiter_messages(self, args: dict):
        max_messages = args.get("max_messages", 100)
        logger.info(f"Finding companies in up to {max_messages} recruiter messages")

        messages = self.jobsearch.get_new_recruiter_messages(max_results=max_messages)
        for i, message in enumerate(messages):
            if not self.running:
                logger.warning("Research daemon stopping, skipping remaining messages")
                return
            logger.info(
                f"Processing message {i+1} of {len(messages)} [max {max_messages}]..."
            )
            try:
                company = self.do_research({"content": message.message or ""})
            except Exception:
                logger.exception("Unexpected error processing recruiter message {i + 1}")
                continue
            if company is None:
                logger.warning("No company extracted from message {i + 1}, skipping")
                continue
            logger.info("Finished processing recruiter messages")

    def do_send_and_archive(self, args: dict):
        """Handle sending a reply and archiving the message."""
        company_id = args.get("company_id")
        if not company_id:
            raise ValueError("Missing company_id in task args")

        logger.info(f"Sending reply and archiving for company: {company_id}")
        company = self.company_repo.get(company_id)
        if not company:
            raise ValueError(f"Company not found: {company_id}")

        if not company.reply_message:
            raise ValueError(f"No reply message for company: {company_id}")

        if not company.recruiter_message or not company.recruiter_message.message_id:
            logger.warning("No recruiter message found for company, skipping")
            return

        logger.info(f"Message ID: {company.recruiter_message.message_id}")

        # Add dry run check before attempting to send
        if not self.dry_run:
            try:
                success = libjobsearch.send_reply_and_archive(
                    thread_id=company.recruiter_message.thread_id,
                    message_id=company.recruiter_message.message_id,
                    reply=company.reply_message,
                    company_id=company_id,
                )

                if success:
                    logger.info(
                        f"Successfully sent reply to {company_id} and archived the thread"
                    )
                else:
                    logger.error(f"Failed to send reply to {company_id}")
                    raise RuntimeError(f"Failed to send reply to {company_id}")
            except Exception as e:
                logger.exception(f"Error sending reply: {e}")
                raise

        # Mark the company as sent/archived in the spreadsheet data
        company.details.current_state = "30. replied to recruiter"
        company.details.updated = datetime.date.today()
        # TODO actually update the spreadsheet
        self.company_repo.update(company)

    def do_ignore_and_archive(self, args: dict):
        """
        Archives a company's message without sending a reply.
        """
        company_id = args["company_id"]
        logger.info(f"Ignoring and archiving message for {company_id}")

        # Get the company
        company = self.company_repo.get(company_id)
        if not company:
            logger.error(f"Company {company_id} not found")
            return {"error": "Company not found"}

        # Archive the message in Gmail
        # TODO: Implement the archiving logic here

        # Record the event
        event = models.Event(
            company_id=company.company_id,
            event_type=models.EventType.ARCHIVED,
        )
        models.company_repository().create_event(event)

        logger.info(f"Successfully archived message for {company_id}")
        # Mark the company as sent/archived in the spreadsheet data
        company.details.current_state = "70. ruled out, without reply"
        company.details.updated = datetime.date.today()
        # TODO actually update the spreadsheet
        self.company_repo.update(company)

        return {"status": "success"}

    def do_import_companies_from_spreadsheet(self, args: dict):
        """Import companies from the spreadsheet into the database.

        This will:
        1. Fetch all company rows from the spreadsheet
        2. For each company, check if it already exists in the DB by normalized name
        3. If it exists, merge the spreadsheet data with the DB data (spreadsheet values take precedence)
        4. If it doesn't exist, create a new company in the DB

        Args:
            args: Task arguments (not used for this task)

        Returns:
            Dict with statistics about the import process
        """
        logger.info("Starting import of companies from spreadsheet")

        # Initialize statistics for tracking progress
        stats = {
            "total_found": 0,
            "processed": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
            "skipped": 0,
            "error_details": [],
        }

        # Get task_id from the TaskStatusContext if available
        current_context = getattr(self, "_current_task_context", None)
        task_id = getattr(current_context, "task_id", None) if current_context else None

        try:
            # Initialize spreadsheet client with the appropriate config
            config = (
                spreadsheet_client.TestConfig
                if self.args.sheet == "test"
                else spreadsheet_client.Config
            )

            sheet_client = MainTabCompaniesClient(
                doc_id=config.SHEET_DOC_ID,
                sheet_id=config.TAB_1_GID,
                range_name=config.TAB_1_RANGE,
            )

            # Get all companies from spreadsheet
            spreadsheet_rows = sheet_client.read_rows_from_google()
            stats["total_found"] = len(spreadsheet_rows)

            # Update task with initial stats if we have a task_id
            if task_id:
                self.task_mgr.update_task(task_id, TaskStatus.RUNNING, result=stats)

            # Process each company from the spreadsheet
            for i, sheet_row in enumerate(spreadsheet_rows):
                stats["processed"] = i + 1

                # Check if daemon is still running
                if not self.running:
                    logger.warning("Import interrupted - daemon shutting down")
                    stats["skipped"] = stats["total_found"] - stats["processed"]
                    break

                try:
                    company_name = sheet_row.name
                    if not company_name:
                        logger.warning(f"Skipping row {i+1} - no company name")
                        stats["skipped"] += 1
                        continue

                    # Normalized name for duplicate checking
                    company_id = normalize_company_name(company_name)

                    # Check if company already exists in database
                    existing_company = self.company_repo.get_by_normalized_name(
                        company_name
                    )

                    if existing_company:
                        # Company exists, merge data (spreadsheet data takes precedence)
                        logger.info(f"Updating existing company: {company_name}")

                        # Prioritize spreadsheet values for all fields
                        for field_name in sheet_row.model_fields.keys():
                            sheet_value = getattr(sheet_row, field_name)
                            # If the sheet value is not empty/None, use it
                            if sheet_value not in (None, "", []):
                                # Special handling for date fields
                                if (
                                    isinstance(sheet_value, datetime.date)
                                    and field_name != "updated"
                                ):
                                    # For date fields except 'updated', use most recent date
                                    db_value = getattr(
                                        existing_company.details, field_name
                                    )
                                    if db_value and db_value > sheet_value:
                                        continue  # Keep the DB value if more recent

                                # Set the value from spreadsheet
                                setattr(existing_company.details, field_name, sheet_value)

                        # Always update the date to today
                        existing_company.details.updated = datetime.date.today()

                        # Update in database
                        self.company_repo.update(existing_company)
                        stats["updated"] += 1
                    else:
                        # Create new company
                        logger.info(f"Creating new company: {company_name}")

                        # Always set the updated date to today
                        sheet_row.updated = datetime.date.today()

                        # Create company with just the basic fields - CompanyStatus doesn't have
                        # imported_from_spreadsheet or imported_at fields
                        new_company = models.Company(
                            company_id=company_id,
                            name=company_name,
                            details=sheet_row,
                            status=models.CompanyStatus(),
                        )

                        # Add import metadata to notes field instead
                        import_note = f"Imported from spreadsheet on {datetime.date.today().isoformat()}"
                        if new_company.details.notes:
                            new_company.details.notes += f"\n{import_note}"
                        else:
                            new_company.details.notes = import_note

                        self.company_repo.create(new_company)
                        stats["created"] += 1

                    # Update task progress every few companies or at the end
                    if task_id and (i % 5 == 0 or i == len(spreadsheet_rows) - 1):
                        self.task_mgr.update_task(
                            task_id, TaskStatus.RUNNING, result=stats
                        )

                except Exception as e:
                    logger.exception(
                        f"Error processing company {getattr(sheet_row, 'name', 'unknown')}"
                    )
                    stats["errors"] += 1
                    stats["error_details"].append(
                        {
                            "company": getattr(sheet_row, "name", "unknown"),
                            "error": str(e),
                        }
                    )

            # Final log of results
            logger.info(
                f"Import completed. Created: {stats['created']}, "
                f"Updated: {stats['updated']}, Errors: {stats['errors']}"
            )

        except Exception as e:
            logger.exception("Error during spreadsheet import")
            stats["errors"] += 1
            stats["error_details"].append(
                {"company": "N/A", "error": f"Global import error: {str(e)}"}
            )

        # Return final stats
        return stats


if __name__ == "__main__":
    parser = libjobsearch.arg_parser()
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually send emails"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode (not headless)",
    )
    parser.set_defaults(recruiter_message_limit=0)
    args = parser.parse_args()

    setup_logging(args.verbose)
    cache_args = libjobsearch.CacheSettings(
        clear_all_cache=args.clear_all_cache,
        clear_cache=args.clear_cache,
        cache_until=args.cache_until,
        no_cache=args.no_cache,
    )
    daemon = ResearchDaemon(args, cache_settings=cache_args)
    daemon.start()
