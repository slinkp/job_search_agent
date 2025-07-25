#!/usr/bin/env python3

import logging
import os
import pty
import signal
import subprocess
import sys
import threading
from typing import Dict, List

import libjobsearch
from logsetup import setup_logging

logger = logging.getLogger(__name__)


def stream_output(fd):
    """Stream output from a file descriptor."""
    with os.fdopen(fd, "rb") as f:
        while True:
            try:
                data = f.read1(1024)
                if not data:
                    break
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            except (OSError, IOError):
                break


def find_process_using_port(port):
    """Find the process using a specific port."""
    try:
        # Try to use lsof to find the process
        result = subprocess.run(
            ["lsof", "-i", f":{port}"], capture_output=True, text=True, check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            # Parse the output to get process info
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:  # Header + at least one process
                process_info = lines[1].split()
                if len(process_info) >= 2:
                    pid = process_info[1]
                    name = process_info[0]
                    return f"Port {port} is in use by process {pid} ({name})"
        return None
    except Exception as e:
        logger.warning(f"Error checking port usage: {e}")
        return None


class ServiceManager:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = True
        self.output_threads: List[threading.Thread] = []

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

            # Create a pseudo-terminal for the research daemon
            research_master_fd, research_slave_fd = pty.openpty()

            research_proc = subprocess.Popen(
                research_cmd,
                stdout=research_slave_fd,
                stderr=research_slave_fd,
                close_fds=True,
                preexec_fn=os.setsid,  # Run in new process group
            )
            os.close(research_slave_fd)  # Close slave fd in parent
            self.processes["research"] = research_proc
            logger.info("Started research daemon")

            # Start output streaming thread for research daemon
            research_thread = threading.Thread(
                target=stream_output, args=(research_master_fd,), daemon=True
            )
            research_thread.start()
            self.output_threads.append(research_thread)

            # Start web server
            server_cmd = ["python", "server/app.py"]
            if args.verbose:
                server_cmd.append("--verbose")

            # Create a pseudo-terminal for the web server
            server_master_fd, server_slave_fd = pty.openpty()

            server_proc = subprocess.Popen(
                server_cmd,
                stdout=server_slave_fd,
                stderr=server_slave_fd,
                close_fds=True,
                preexec_fn=os.setsid,  # Run in new process group
            )
            os.close(server_slave_fd)  # Close slave fd in parent
            self.processes["server"] = server_proc
            logger.info("Started web server")

            # Start output streaming thread for web server
            server_thread = threading.Thread(
                target=stream_output, args=(server_master_fd,), daemon=True
            )
            server_thread.start()
            self.output_threads.append(server_thread)

            # Wait for processes to complete
            while self.running:
                for name, proc in self.processes.items():
                    if proc.poll() is not None:
                        exit_code = proc.poll()
                        error_msg = (
                            f"{name} service died unexpectedly with exit code {exit_code}"
                        )

                        # Check if it's a port in use error for the server
                        if name == "server" and exit_code != 0:
                            port_info = find_process_using_port(
                                8080
                            )  # Default port for the server
                            if port_info:
                                error_msg += f"\n{port_info}"

                        logger.error(error_msg)
                        self.handle_shutdown(None, None)
                        break

        except Exception as e:
            logger.error(f"Error starting services: {e}")
            self.handle_shutdown(None, None)

    def handle_shutdown(self, signum, frame):
        logger.info("Shutting down services...")
        self.running = False

        # First try to gracefully shut down the server
        if "server" in self.processes and self.processes["server"].poll() is None:
            logger.info("Sending SIGINT to server for graceful shutdown...")
            os.killpg(os.getpgid(self.processes["server"].pid), signal.SIGINT)

            # Wait for server to exit gracefully
            try:
                self.processes["server"].wait(timeout=10)
                logger.info("Server shut down gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Server didn't shut down within 10 seconds, sending SIGTERM..."
                )
                os.killpg(os.getpgid(self.processes["server"].pid), signal.SIGTERM)
                try:
                    self.processes["server"].wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Server still running after SIGTERM, forcing shutdown..."
                    )
                    os.killpg(os.getpgid(self.processes["server"].pid), signal.SIGKILL)

        # Then shut down the research daemon
        if "research" in self.processes and self.processes["research"].poll() is None:
            logger.info("Shutting down research daemon...")
            os.killpg(os.getpgid(self.processes["research"].pid), signal.SIGTERM)
            try:
                self.processes["research"].wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Research daemon didn't terminate gracefully, forcing...")
                os.killpg(os.getpgid(self.processes["research"].pid), signal.SIGKILL)

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
    setup_logging(args.verbose, process_name="combined")

    manager = ServiceManager()
    manager.start_services(args)


if __name__ == "__main__":
    main()
