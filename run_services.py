#!/usr/bin/env python3

import logging
import signal
import subprocess
import sys

import libjobsearch
from logsetup import setup_logging

logger = logging.getLogger(__name__)


class ServiceManager:
    def __init__(self):
        self.processes: dict[str, subprocess.Popen] = {}
        self.running = True

        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def start_services(self, args):
        try:
            # Start research daemon
            research_cmd = [
                "python",
                "research_daemon.py",
                "--model",
                args.model,
                "--rag-message-limit",
                str(args.rag_message_limit),
                "--sheet",
                args.sheet,
            ]

            # Add optional arguments if they were specified
            if args.verbose:
                research_cmd.append("--verbose")
            if args.no_cache:
                research_cmd.append("--no-cache")
            if args.clear_all_cache:
                research_cmd.append("--clear-all-cache")
            if args.clear_cache:
                for step in args.clear_cache:
                    research_cmd.extend(["--clear-cache", step.name])
            if args.cache_until:
                research_cmd.extend(["--cache-until", args.cache_until.name])
            if args.dry_run:
                research_cmd.append("--dry-run")
            if args.no_headless:
                research_cmd.append("--no-headless")
            if args.test_messages:
                for msg in args.test_messages:
                    research_cmd.extend(["--test-messages", msg])
            if args.recruiter_message_limit:
                research_cmd.extend(
                    ["--recruiter-message-limit", str(args.recruiter_message_limit)]
                )

            research_proc = subprocess.Popen(
                research_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            self.processes["research"] = research_proc
            logger.info("Started research daemon")

            # Start web server
            server_cmd = ["python", "server/app.py"]
            if args.verbose:
                server_cmd.append("--verbose")

            server_proc = subprocess.Popen(
                server_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            self.processes["server"] = server_proc
            logger.info("Started web server")

            # Wait for processes to complete
            while self.running:
                for procname, proc in self.processes.items():
                    if proc.poll() is not None:
                        logger.error(f"{procname} died unexpectedly")
                        self.handle_shutdown(None, None)
                        break

        except Exception as e:
            logger.error(f"Error starting services: {e}")
            self.handle_shutdown(None, None)

    def handle_shutdown(self, signum, frame):
        logger.info("Shutting down services...")
        self.running = False

        for procname, proc in self.processes.items():
            if proc.poll() is None:  # If process is still running
                proc.terminate()
                try:
                    proc.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
                except subprocess.TimeoutExpired:
                    logger.warning(
                        f"Process {procname} didn't terminate gracefully, forcing..."
                    )
                    proc.kill()

        sys.exit(0)


def main():
    # Get the base argument parser from libjobsearch
    parser = libjobsearch.arg_parser()

    # Add research daemon specific arguments
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

    manager = ServiceManager()
    manager.start_services(args)


if __name__ == "__main__":
    main()
