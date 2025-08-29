import argparse
import datetime
import logging
import signal
import time
from typing import Any, Optional

import libjobsearch
import models
import spreadsheet_client
from email_client import GmailRepliesSearcher
from logsetup import setup_logging
from tasks import TaskManager, TaskStatus, TaskType, task_manager

logger = logging.getLogger("research_daemon")


class TaskStatusContext:

    def __init__(self, task_mgr: TaskManager, task_id: str, task_type: TaskType):
        self.task_mgr = task_mgr
        self.task_id = task_id
        self.task_type = task_type
        # Use Any type to allow any result type
        self.result: Any = None

    def __enter__(self):
        self.task_mgr.update_task(self.task_id, TaskStatus.RUNNING)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            # Only include result if it's not None
            if self.result is not None:
                # When result is a Company object, only store its company_id to avoid serialization issues
                if isinstance(self.result, models.Company):
                    result = {"company_id": self.result.company_id}
                else:
                    result = self.result
                self.task_mgr.update_task(
                    self.task_id,
                    TaskStatus.COMPLETED,
                    result=result,
                )
            else:
                logger.info(f"Setting task {self.task_id} to COMPLETED with no result")
                self.task_mgr.update_task(self.task_id, TaskStatus.COMPLETED)
        else:
            logger.error(f"Task {self.task_id} failed with error: {str(exc_value)}")
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
        # TODO: headless isn't actually passed down to libjobsearch
        # and to linkedin ... and would it work??
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
            with TaskStatusContext(self.task_mgr, task_id, task_type) as context:
                result = None
                if task_type == TaskType.COMPANY_RESEARCH:
                    result = self.do_research(task_args)
                elif task_type == TaskType.GENERATE_REPLY:
                    result = self.do_generate_reply(task_args)
                elif task_type == TaskType.FIND_COMPANIES_FROM_RECRUITER_MESSAGES:
                    result = self.do_find_companies_in_recruiter_messages(task_args)
                elif task_type == TaskType.SEND_AND_ARCHIVE:
                    result = self.do_send_and_archive(task_args)
                elif task_type == TaskType.IGNORE_AND_ARCHIVE:
                    result = self.do_ignore_and_archive(task_args)
                elif task_type == TaskType.IMPORT_COMPANIES_FROM_SPREADSHEET:
                    result = self.do_import_companies_from_spreadsheet(task_args)
                    logger.info(f"Import companies result: {result}")
                else:
                    logger.error(f"Ignoring unsupported task type: {task_type}")

                # Only set the result if it's not None
                if result is not None:
                    logger.info(
                        f"Setting result on task context for task {task_id}: {result}"
                    )
                    context.result = result
                else:
                    logger.warning(
                        f"No result returned from task handler for task {task_id}"
                    )
                logger.info(f"Task {task_id} completed")

    def _generate_company_id(self, name: str) -> str:
        """Generate a company ID from a name by normalizing it."""
        return models.normalize_company_name(name)

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
                "No searchable found via any of content, name, url, or existing company"
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
        recruiter_message = args.get("recruiter_message")

        # If we have a company_id, try to get the existing company
        existing = None
        if company_id:
            existing = self.company_repo.get(company_id)
        elif company_name:
            # If we have a company name, try to find an existing company with that name
            existing = self.company_repo.get_by_normalized_name(company_name)

        if existing and existing.recruiter_message and not recruiter_message:
            recruiter_message = existing.recruiter_message

        # If we have a RecruiterMessage object, use it directly for research
        if recruiter_message:
            content_or_message = recruiter_message
            # For RecruiterMessage, we'll let the research method extract the company name
            # but we can use any provided company_name as a fallback
        else:
            # Determine what content to use for research
            content_for_research = self.get_content_for_research(
                company=existing,
                company_name=company_name,
                company_url=company_url,
                content=content,
            )
            content_or_message = content_for_research["content"]
            if content_or_message is None:
                raise ValueError("No content for research")

            company_name = content_for_research["company_name"]
            company_url = content_for_research["company_url"]

        result_company = None
        company = None
        try:
            company = self.jobsearch.research_company(
                content_or_message, model=self.ai_model
            )

            # Log any research errors that occurred
            research_errors = company.status.research_errors
            if research_errors:
                logger.warning(f"Research completed with {len(research_errors)} errors:")
                for err in research_errors:
                    logger.warning(f"  - {err.step}: {err.error}")

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
                    # Log potential duplicates by alias/name overlap (non-blocking)
                    try:
                        overlaps = self.company_repo.find_potential_duplicates(company.company_id)
                        if overlaps:
                            logger.warning(
                                f"Potential duplicates detected for {company.company_id}: {overlaps}"
                            )
                    except Exception:
                        logger.exception("Duplicate detection failed during research")
                    result_company = company

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
                result_company = existing
            else:
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
                    company_id=self._generate_company_id(company_name),
                    name=company_name,
                    details=minimal_row,
                    status=company_status,
                )

                self.company_repo.create(company)
                result_company = company

        if result_company is not None:
            try:
                libjobsearch.upsert_company_in_spreadsheet(
                    result_company.details, self.args
                )
            except Exception as spreadsheet_error:
                logger.exception(f"Failed to update spreadsheet: {spreadsheet_error}")
                raise
        return result_company

    def do_generate_reply(self, args: dict):
        assert "company_id" in args
        company = self.company_repo.get(args["company_id"])
        assert company is not None
        assert company.recruiter_message is not None
        logger.info(f"Generating reply for {company.company_id}")
        # TODO: Include more company info context in reply args
        reply = self.jobsearch.generate_reply(company.initial_message)
        company.reply_message = reply
        self.company_repo.update(company)
        # Record activity: reply generated
        try:
            self.company_repo.update_activity(
                company.company_id,
                datetime.datetime.now(datetime.timezone.utc),
                "reply generated",
            )
        except Exception:
            logger.exception("Failed to update activity for reply generated")
        logger.info(f"Updated reply for {company.company_id}")

    def do_find_companies_in_recruiter_messages(self, args: dict):
        max_messages = args.get("max_messages", None)
        do_research = args.get("do_research", False)

        # If max_messages is None, fetch all messages (use a very large number)
        if max_messages is None:
            max_messages = 10000  # Large enough to fetch all messages
            logger.info(
                f"Finding companies in all recruiter messages (do_research={do_research})"
            )
        else:
            logger.info(
                f"Finding companies in up to {max_messages} recruiter messages (do_research={do_research})"
            )

        messages = self.jobsearch.get_new_recruiter_messages(max_results=max_messages)
        logger.info(f"Retrieved {len(messages)} messages from Gmail")

        processed_count = 0
        skipped_count = 0

        for i, message in enumerate(messages):
            if not self.running:
                logger.warning("Research daemon stopping, skipping remaining messages")
                return

            # Check if message already exists in database
            existing_message = self.company_repo.get_recruiter_message_by_id(
                message.message_id
            )
            if existing_message:
                logger.info(
                    f"Message {message.message_id} already exists in database, skipping"
                )
                skipped_count += 1
                continue

            logger.info(
                f"Processing message {i+1} of {len(messages)} [max {max_messages}]..."
            )
            try:
                if do_research:
                    # Pass the full RecruiterMessage object instead of just the content
                    company = self.do_research({"recruiter_message": message})
                    if company is None:
                        logger.warning(
                            f"No company extracted from message {i + 1}, skipping"
                        )
                        continue
                else:
                    # Just create a basic company object without research
                    company = self.create_basic_company_from_message(message)
                    if company is None:
                        logger.warning(
                            f"No company extracted from message {i + 1}, skipping"
                        )
                        continue
                # After creating/updating company, log potential duplicates (non-blocking)
                try:
                    if company:
                        overlaps = self.company_repo.find_potential_duplicates(company.company_id)
                        if overlaps:
                            logger.warning(
                                f"Potential duplicates detected for {company.company_id}: {overlaps}"
                            )
                except Exception:
                    logger.exception("Duplicate detection failed during email ingestion")
                processed_count += 1
            except Exception:
                logger.exception(f"Unexpected error processing recruiter message {i + 1}")
                continue

        logger.info(
            f"Finished processing recruiter messages: {processed_count} processed, {skipped_count} skipped"
        )

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
        Supports both company-level and message-level archiving.
        """
        company_id = args["company_id"]
        message_id = args.get(
            "message_id"
        )  # Optional message_id for specific message archiving

        logger.info(
            f"Ignoring and archiving message for {company_id}"
            + (f" (message_id: {message_id})" if message_id else "")
        )

        # Get the company
        company = self.company_repo.get(company_id)
        if not company:
            logger.error(f"Company {company_id} not found")
            return {"error": "Company not found"}

        # Archive the message in Gmail if message_id is provided
        if company and not message_id:
            message_id = company.message_id

        if message_id:
            try:
                email_searcher = GmailRepliesSearcher()
                email_searcher.authenticate()

                success = email_searcher.label_and_archive_message(message_id)
                if success:
                    logger.info(f"Successfully archived message {message_id} in Gmail")
                else:
                    logger.error(f"Failed to archive message {message_id} in Gmail")
                    return {"error": "Failed to archive message in Gmail"}
            except Exception as e:
                logger.exception(f"Error archiving message {message_id} in Gmail: {e}")
                return {"error": f"Error archiving message in Gmail: {str(e)}"}
        else:
            # TODO: Implement company-level archiving logic here
            logger.warning("Company-level archiving not yet implemented")

        # Record the event.

        event = models.Event(
            company_id=company.company_id,
            event_type=models.EventType.ARCHIVED,
        )
        models.company_repository().create_event(event)

        logger.info(f"Successfully archived message for {company_id}")
        # Mark the company as sent/archived in the spreadsheet data
        company.details.current_state = "70. ruled out, without reply"
        company.details.updated = company.status.archived_at = datetime.datetime.now()
        # TODO actually update the spreadsheet
        self.company_repo.update(company)

        return {"status": "success"}

    def create_basic_company_from_message(
        self, message: models.RecruiterMessage
    ) -> Optional[models.Company]:
        """
        Create a basic Company object from a RecruiterMessage without doing any research.

        This creates a minimal Company object with the RecruiterMessage attached,
        but does NO research at all - not even initial research.
        """
        try:
            # Create a basic company with minimal info from the message
            # We'll use a placeholder name that can be updated later when research is done
            placeholder_name = f"Company from {message.sender}"
            company_id = models.normalize_company_name(placeholder_name)

            # Create basic company details
            company_details = models.CompaniesSheetRow(
                name=placeholder_name,
                updated=datetime.date.today(),
                current_state="10. consider applying",  # Default initial state
                email_thread_link=message.email_thread_link,
            )

            # Create the company object
            company = models.Company(
                company_id=company_id,
                name=placeholder_name,
                details=company_details,
                status=models.CompanyStatus(),
                recruiter_message=message,
            )

            # Set the company_id on the recruiter message
            if company.recruiter_message:
                company.recruiter_message.company_id = company_id

            # Check if company already exists by normalized name
            existing = self.company_repo.get_by_normalized_name(company.name)
            if existing:
                logger.info(
                    f"Found existing company with normalized name match: {existing.name}"
                )
                # Update the existing company with the new recruiter message
                existing.recruiter_message = message
                existing.recruiter_message.company_id = existing.company_id
                self.company_repo.update(existing)
                return existing
            else:
                # Create a new company
                logger.info(f"Creating basic company {company.name} without any research")
                self.company_repo.create(company)
                return company

        except Exception as e:
            logger.exception(f"Error creating basic company from message: {e}")
            return None

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
        stats: dict[str, Any] = {
            "total_found": 0,
            "processed": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
            "skipped": 0,
            "error_details": [],
            "current_company": None,
            "percent_complete": 0,
            "start_time": datetime.datetime.now(datetime.timezone.utc),
            "end_time": None,
            "duration_seconds": 0,
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

            sheet_client = spreadsheet_client.MainTabCompaniesClient(
                doc_id=config.SHEET_DOC_ID,
                sheet_id=config.TAB_1_GID,
                range_name=config.TAB_1_RANGE,
            )

            # Get all companies from spreadsheet
            spreadsheet_rows = sheet_client.read_rows_from_google()
            stats["total_found"] = len(spreadsheet_rows)
            logger.info(f"Found {stats['total_found']} companies in spreadsheet")

            # Update task with initial stats if we have a task_id
            if task_id:
                # Ensure processed is 0 for initial update
                stats["processed"] = 0
                stats["percent_complete"] = 0
                logger.info(f"Updating task {task_id} with initial stats: {stats}")
                self.task_mgr.update_task(task_id, TaskStatus.RUNNING, result=stats)

            # Process each company from the spreadsheet
            for i, sheet_row in enumerate(spreadsheet_rows):
                stats["processed"] = i + 1
                if len(spreadsheet_rows) > 0:
                    stats["percent_complete"] = int((i + 1) / len(spreadsheet_rows) * 100)

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

                    # Update current company being processed
                    stats["current_company"] = company_name
                    logger.info(
                        f"Processing company {i+1}/{stats['total_found']}: {company_name}"
                    )

                    # Normalized name for duplicate checking
                    company_id = models.normalize_company_name(company_name)

                    # Check both ways if company already exists in database
                    existing_company = self.company_repo.get(company_id=company_id)
                    if not existing_company:
                        existing_company = self.company_repo.get_by_normalized_name(
                            company_name
                        )

                    if existing_company:
                        # Company exists, merge data (spreadsheet data takes precedence)
                        logger.info(f"Updating existing company: {company_name}")
                        models.merge_company_data(existing_company, sheet_row)

                        # Mark as imported and set timestamp
                        existing_company.status.imported_from_spreadsheet = True
                        existing_company.status.imported_at = datetime.datetime.now(
                            datetime.timezone.utc
                        )

                        self.company_repo.update(existing_company)
                        stats["updated"] += 1
                    else:
                        # Create new company
                        logger.info(f"Creating new company: {company_name}")

                        if not sheet_row.updated:
                            sheet_row.updated = datetime.date.today()

                        # Create a new company, using status from existing company if found
                        new_company = models.Company(
                            company_id=company_id,
                            name=company_name,
                            details=models.CompaniesSheetRow(),  # Start with empty details
                            status=(
                                models.CompanyStatus(
                                    imported_from_spreadsheet=True,
                                    imported_at=datetime.datetime.now(
                                        datetime.timezone.utc
                                    ),
                                )
                            ),
                        )

                        # Then use merge_company_data to properly merge the spreadsheet data
                        new_company = models.merge_company_data(new_company, sheet_row)

                        self.company_repo.create(new_company)
                        stats["created"] += 1

                    # Update task progress every few companies or at the end
                    if task_id and (i % 5 == 0 or i == len(spreadsheet_rows) - 1):
                        logger.info(f"Updating task {task_id} with progress: {stats}")
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
                f"Updated: {stats['updated']}, Errors: {stats['errors']} "
                f"Skipped: {stats['skipped']}, Total: {stats['total_found']}"
            )

        except Exception as e:
            logger.exception("Error during spreadsheet import")
            stats["errors"] += 1
            stats["error_details"].append(
                {"company": "N/A", "error": f"Global import error: {str(e)}"}
            )

        # Record end time and calculate duration
        stats["end_time"] = datetime.datetime.now(datetime.timezone.utc)
        stats["duration_seconds"] = (
            stats["end_time"] - stats["start_time"]
        ).total_seconds()

        # Generate and log summary
        summary = self.format_import_summary(stats)
        logger.info(f"Import summary:\n{summary}")

        # Log final stats that will be returned
        logger.info(f"Returning final import stats: {stats}")

        # Return final stats
        return stats

    def format_import_summary(self, stats: dict) -> str:
        """Format import statistics into a human-readable summary.

        Args:
            stats: Dictionary containing import statistics

        Returns:
            Formatted summary as a string
        """
        if not stats.get("end_time"):
            stats["end_time"] = datetime.datetime.now(datetime.timezone.utc)

        if not stats.get("duration_seconds") and stats.get("start_time"):
            stats["duration_seconds"] = (
                stats["end_time"] - stats["start_time"]
            ).total_seconds()

        duration_str = f"{stats['duration_seconds']:.1f} seconds"
        if stats["duration_seconds"] > 60:
            minutes = stats["duration_seconds"] / 60
            duration_str = f"{minutes:.1f} minutes"

        summary = [
            "=" * 40,
            "SPREADSHEET IMPORT SUMMARY",
            "=" * 40,
            f"Start time: {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"End time: {stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {duration_str}",
            f"Companies found in spreadsheet: {stats['total_found']}",
            f"Companies processed: {stats['processed']}",
            "-" * 40,
            f"Companies created: {stats['created']}",
            f"Companies updated: {stats['updated']}",
            f"Companies skipped: {stats['skipped']}",
            f"Errors encountered: {stats['errors']}",
        ]

        # Add error details if any
        if stats.get("errors", 0) > 0 and stats.get("error_details"):
            summary.append("-" * 40)
            summary.append("Error details:")
            for i, error in enumerate(stats["error_details"], 1):
                summary.append(
                    f"{i}. {error.get('company', 'Unknown')}: {error.get('error', 'Unknown error')}"
                )

        return "\n".join(summary)


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

    setup_logging(args.verbose, process_name="research_daemon")
    cache_args = libjobsearch.CacheSettings(
        clear_all_cache=args.clear_all_cache,
        clear_cache=args.clear_cache,
        cache_until=args.cache_until,
        no_cache=args.no_cache,
    )
    daemon = ResearchDaemon(args, cache_settings=cache_args)
    daemon.start()
