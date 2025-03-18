import argparse
import datetime
import logging
import signal
import time

import libjobsearch
import models
from logsetup import setup_logging
from tasks import TaskManager, TaskStatus, TaskType, task_manager

logger = logging.getLogger(__name__)


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

    def stop(self, signum=None, frame=None):
        logger.info("Research daemon stopping")
        self.running = False

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
                else:
                    logger.error(f"Ignoring unsupported task type: {task_type}")
                logger.info(f"Task {task_id} completed")

    def do_research(self, args: dict):
        company_name = args["company_name"]
        existing = self.company_repo.get(company_name)
        content = company_name
        recruiter_message = None
        if existing:
            recruiter_message = existing.recruiter_message
            if recruiter_message:
                content = recruiter_message.message
                logger.info(f"Using existing initial message: {content[:400]}")

        # TODO: Pass more context from email, etc.
        company_row = self.jobsearch.research_company(content, model=self.ai_model)
        if existing:
            logger.info(f"Updating company {company_name}")
            existing.details = company_row
            self.company_repo.update(existing)
        else:
            logger.info(f"Creating company {company_name}")
            company = models.Company(
                name=company_name,
                details=company_row,
            )
            self.company_repo.create(company)

        # Update the spreadsheet with the researched company data
        libjobsearch.upsert_company_in_spreadsheet(company_row, self.args)

    def do_generate_reply(self, args: dict):
        # TODO: Use LLM to generate reply
        assert "company_name" in args
        company = self.company_repo.get(args["company_name"])
        assert company is not None
        assert company.recruiter_message is not None
        logger.info(f"Generating reply for {args['company_name']}")
        # TODO: Include more company info context in reply args
        reply = self.jobsearch.generate_reply(company.initial_message)
        company.reply_message = reply
        self.company_repo.update(company)
        logger.info(f"Updated reply for {args['company_name']}")

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
                company_row = self.jobsearch.research_company(
                    message,
                    model=self.ai_model,
                    do_advanced=args.get("do_research", False),
                )
                if company_row.name is None:
                    logger.warning(f"No company extracted from message, skipping")
                    continue

                if self.company_repo.get(company_row.name) is not None:
                    logger.info(f"Company {company_row.name} already exists, skipping")
                    continue

                thread_id = None
                if getattr(message, "email_thread_link", None):
                    # Extract thread_id from the URL format like:
                    # https://mail.google.com/mail/u/0/#label/jobs+2024%2Frecruiter+pings/thread-id
                    parts = message.email_thread_link.split("/")
                    if len(parts) > 0:
                        thread_id = parts[-1]

                message_id = message.message_id

                company = models.Company(
                    name=company_row.name,
                    details=company_row,
                    message_id=message_id,
                    recruiter_message=message,
                )
                self.company_repo.create(company)
                logger.info(f"Created company {company_row.name} from recruiter message")
            except Exception:
                logger.exception("Error processing recruiter message")
                continue
        logger.info("Finished processing recruiter messages")

    def do_send_and_archive(self, args: dict):
        """Handle sending a reply and archiving the message."""
        company_name = args.get("company_name")
        if not company_name:
            raise ValueError("Missing company_name in task args")

        logger.info(f"Sending reply and archiving for company: {company_name}")
        company = self.company_repo.get(company_name)
        if not company:
            raise ValueError(f"Company not found: {company_name}")

        if not company.reply_message:
            raise ValueError(f"No reply message for company: {company_name}")

        if not company.message_id:
            raise ValueError(f"No message ID for company: {company_name}")

        # In dry run mode, just log what would happen
        if self.dry_run:
            logger.info("DRY RUN: Would send the following email:")
            logger.info(f"To: Recruiter at {company_name}")
            logger.info(f"Thread: {company.thread_id}")
            logger.info(f"Message ID: {company.message_id}")
            logger.info(f"Message:\n{company.reply_message}")
            logger.info("DRY RUN: Would archive the message thread")
            return

        # We have a message ID, use it
        try:
            success = libjobsearch.send_reply_and_archive(
                message_id=company.message_id,
                thread_id=company.thread_id,
                reply=company.reply_message,
                company_name=company.name,
            )

            if success:
                logger.info(
                    f"Successfully sent reply to {company_name} and archived the thread"
                )
            else:
                logger.error(f"Failed to send reply to {company_name}")
                raise RuntimeError(f"Failed to send reply to {company_name}")
        except Exception as e:
            logger.exception(f"Error sending reply: {e}")
            raise

        # Mark the company as sent/archived in the database
        company.details.current_state = "30. replied to recruiter"
        company.details.updated = datetime.date.today()
        self.company_repo.update(company)


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
