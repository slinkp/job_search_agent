import datetime
import json
import logging
import logging.handlers
import os

import colorama
from colorama import Fore, Style
from pyramid.config import Configurator  # type: ignore[import-untyped]
from pyramid.renderers import JSON  # type: ignore[import-untyped]
from pyramid.response import Response  # type: ignore[import-untyped]
from pyramid.scripts.pserve import PServeCommand  # type: ignore[import-untyped]
from pyramid.view import view_config  # type: ignore[import-untyped]

import models
import tasks
from logsetup import setup_logging

# Get our application logger
logger = logging.getLogger("server.app")


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Save original levelname
        orig_levelname = record.levelname
        # Color the levelname
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"

        # Color the name and message differently for different loggers
        if record.name.startswith("pyramid"):
            record.name = f"{Fore.MAGENTA}{record.name}{Style.RESET_ALL}"
        else:
            record.name = f"{Fore.BLUE}{record.name}{Style.RESET_ALL}"

        # Format with colors
        result = super().format(record)
        # Restore original levelname
        record.levelname = orig_levelname
        return result


def setup_colored_logging():
    # Initialize colorama
    colorama.init()

    # Set up handler with our custom formatter
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter("%(levelname)-8s %(name)s: %(message)s"))

    # Configure root logger
    root_logger = logging.getLogger()
    # Remove only StreamHandler instances (console handlers), keep file handlers
    for h in root_logger.handlers[:]:
        if isinstance(h, logging.StreamHandler) and not isinstance(
            h, logging.handlers.RotatingFileHandler
        ):
            root_logger.removeHandler(h)
    # Add our colored console handler
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


@view_config(route_name="company", renderer="json", request_method="GET")
def get_company(request) -> dict:
    company_id = request.matchdict["company_id"]
    repo = models.company_repository()
    company = repo.get(company_id)

    if not company:
        request.response.status = 404
        return {"error": "Company not found"}

    company_dict = get_company_dict_with_status(company, repo)
    return company_dict


def get_company_dict_with_status(
    company: models.Company, repo: models.CompanyRepository
) -> dict:
    company_dict = models.serialize_company(company)

    # Format research errors as a readable string to avoid [object Object] display
    if company.status.research_errors:
        formatted_errors = []
        for err in company.status.research_errors:
            formatted_errors.append(f"{err.step}: {err.error}")
        company_dict["research_errors"] = "; ".join(formatted_errors)

    # Include status fields directly in the response
    company_dict["research_status"] = company.status.research_status
    company_dict["sent_at"] = company.status.reply_sent_at
    company_dict["archived_at"] = company.status.archived_at
    company_dict["promising"] = company.details.promising

    return company_dict


@view_config(route_name="companies", renderer="json", request_method="GET")
def get_companies(request) -> list[dict]:
    repo = models.company_repository()
    companies = repo.get_all(include_messages=True)

    # Check if we should include all companies or filter out replied/archived
    include_all = request.params.get("include_all", "").lower() == "true"

    company_data = []
    for company in companies:
        # Filter out companies that have been replied to or archived
        if not include_all:
            if company.status.reply_sent_at or company.status.archived_at:
                continue

        company_dict = get_company_dict_with_status(company, repo)
        company_data.append(company_dict)

    return company_data


@view_config(route_name="messages", renderer="json", request_method="GET")
def get_messages(request) -> list[dict]:
    """Get all recruiter messages with company info.

    Note: Reply messages are currently stored at the company level (Company.reply_message).
    If a company has multiple messages, all messages from that company will show
    the same reply_message content. The reply_status is calculated per message
    based on the message's reply_sent_at field and the company's reply_message.
    """
    repo = models.company_repository()
    messages = repo.get_all_messages()

    message_data = []
    for message in messages:
        message_dict = message.model_dump()
        message_dict["company_name"] = getattr(
            message, "_company_name", "Unknown Company"
        )

        # Add reply_message from company
        reply_message = getattr(message, "_reply_message", "")
        message_dict["reply_message"] = reply_message

        # Calculate reply_status based on reply_sent_at and reply_message
        if message.reply_sent_at:
            reply_status = "sent"
        elif reply_message and reply_message.strip():
            reply_status = "generated"
        else:
            reply_status = "none"

        message_dict["reply_status"] = reply_status
        message_data.append(message_dict)

    return message_data


@view_config(route_name="home")
def home(request):
    # Read and return the index.html file
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "static", "index.html")) as f:
        return Response(f.read(), content_type="text/html")


def create_stub_message(company_name: str) -> str:
    return f"generated reply {company_name} {datetime.datetime.now().isoformat()}"


@view_config(route_name="message_reply", renderer="json", request_method="POST")
def generate_message_by_id(request):
    """Generate a reply for a specific message by message_id.

    Note: Currently, reply drafts are stored at the company level (Company.reply_message).
    If a company has multiple messages, generating a reply for one message will
    update the company's shared reply draft. This is a temporary limitation until
    per-message draft storage is implemented.
    """
    message_id = request.matchdict["message_id"]

    if not message_id:
        request.response.status = 400
        return {"error": "Message ID is required"}

    repo = models.company_repository()
    message = repo.get_recruiter_message_by_id(message_id)

    if not message:
        request.response.status = 404
        return {"error": "Message not found"}

    # Get the company associated with this message
    company = repo.get(message.company_id)
    if not company:
        request.response.status = 404
        return {"error": "Company not found for this message"}

    task_id = tasks.task_manager().create_task(
        tasks.TaskType.GENERATE_REPLY,
        {"company_id": company.company_id},
    )
    logger.info(
        f"Generate reply requested for message {message_id} (company: {company.name}), task_id: {task_id}"
    )

    return {"task_id": task_id, "status": tasks.TaskStatus.PENDING.value}


@view_config(route_name="message_reply", renderer="json", request_method="PUT")
def update_message_by_id(request):
    """Update a reply message for a specific message by message_id.

    Note: Currently, reply drafts are stored at the company level (Company.reply_message).
    If a company has multiple messages, updating a reply for one message will
    update the company's shared reply draft. This is a temporary limitation until
    per-message draft storage is implemented.
    """
    message_id = request.matchdict["message_id"]

    if not message_id:
        request.response.status = 400
        return {"error": "Message ID is required"}

    try:
        body = request.json_body
        if body is None:
            request.response.status = 400
            return {"error": "Invalid JSON"}
        message = body.get("message")
        if not message:
            request.response.status = 400
            return {"error": "Message is required"}
    except json.JSONDecodeError:
        request.response.status = 400
        return {"error": "Invalid JSON"}

    repo = models.company_repository()
    recruiter_message = repo.get_recruiter_message_by_id(message_id)

    if not recruiter_message:
        request.response.status = 404
        return {"error": "Message not found"}

    # Get the company associated with this message
    company = repo.get(recruiter_message.company_id)
    if not company:
        request.response.status = 404
        return {"error": "Company not found for this message"}

    # Update the company's reply message
    company.reply_message = message
    repo.update(company)

    logger.info(
        f"Updated reply message for message {message_id} (company: {company.name}): {message}"
    )
    return models.serialize_company(company)


@view_config(route_name="research", renderer="json", request_method="POST")
def research_company(request):
    company_id = request.matchdict["company_id"]
    company = models.company_repository().get(company_id)

    if not company:
        request.response.status = 404
        return {"error": "Company not found"}

    # Create a new task
    task_id = tasks.task_manager().create_task(
        tasks.TaskType.COMPANY_RESEARCH,
        {"company_id": company.company_id, "company_name": company.name},
    )
    logger.info(f"Research requested for {company.name}, task_id: {task_id}")

    # When research is completed, we'll set this timestamp
    # For now, just return the task info
    return {
        "task_id": task_id,
        "status": tasks.TaskStatus.PENDING.value,
        # We'll set research_completed_at when the task completes
    }


@view_config(route_name="task_status", renderer="json", request_method="GET")
def get_task_status(request):
    task_id = request.matchdict["task_id"]
    task = tasks.task_manager().get_task(task_id)

    if not task:
        request.response.status = 404
        return {"error": "Task not found"}

    # Log task details for debugging
    status_value = task["status"].value if task["status"] else "None"
    has_result = task["result"] is not None
    result_summary = str(task["result"])[:200] + "..." if task["result"] else "None"

    logger.info(
        f"Returning task {task_id} status: {status_value}, has_result: {has_result}"
    )
    logger.info(f"Task result summary: {result_summary}")

    if task["status"].value == "completed" and not has_result:
        logger.warning(f"Task {task_id} is completed but has no result data!")

    return task


@view_config(route_name="scan_recruiter_emails", renderer="json", request_method="POST")
def scan_recruiter_emails(request):
    max_messages = request.json_body.get("max_messages", None)
    do_research = request.json_body.get("do_research", False)
    task_id = tasks.task_manager().create_task(
        tasks.TaskType.FIND_COMPANIES_FROM_RECRUITER_MESSAGES,
        {"max_messages": max_messages, "do_research": do_research},
    )
    logger.info(
        f"Email scan requested with do_research={do_research}, task_id: {task_id}"
    )
    return {"task_id": task_id, "status": tasks.TaskStatus.PENDING.value}


@view_config(
    route_name="send_and_archive_message", renderer="json", request_method="POST"
)
def send_and_archive_message(request):
    """Send and archive a specific message by message_id, implicitly saving the current draft first."""
    message_id = request.matchdict.get("message_id")

    if not message_id:
        request.response.status = 400
        return {"error": "Message ID is required"}

    repo = models.company_repository()
    message = repo.get_recruiter_message_by_id(message_id)

    if not message:
        request.response.status = 404
        return {"error": "Message not found"}

    # Get the company associated with this message
    company = repo.get(message.company_id)
    if not company:
        request.response.status = 404
        return {"error": "Company not found for this message"}

    if not company.reply_message:
        request.response.status = 400
        return {"error": "No reply message to send"}

    # Create a new task for sending and archiving
    task_id = tasks.task_manager().create_task(
        tasks.TaskType.SEND_AND_ARCHIVE,
        {"company_id": company.company_id},
    )

    # Set archived_at and reply_sent_at status fields
    current_time = datetime.datetime.now(datetime.timezone.utc)
    company.status.archived_at = current_time
    company.status.reply_sent_at = current_time
    repo.update(company)

    # Also set reply_sent_at and archived_at on the specific message
    message.reply_sent_at = current_time
    message.archived_at = current_time
    repo.create_recruiter_message(message)  # This will update via upsert

    logger.info(
        f"Send and archive requested for message {message_id} (company: {company.name}), task_id: {task_id}"
    )

    return {
        "task_id": task_id,
        "status": tasks.TaskStatus.PENDING.value,
        "sent_at": current_time.isoformat(),
        "archived_at": current_time.isoformat(),
        "message_id": message_id,
    }


@view_config(route_name="send_and_archive", renderer="json", request_method="POST")
def send_and_archive(request):
    company_id = request.matchdict["company_id"]
    company = models.company_repository().get(company_id)

    if not company:
        request.response.status = 404
        return {"error": "Company not found"}

    if not company.reply_message:
        request.response.status = 400
        return {"error": "No reply message to send"}

    # Create a new task for sending and archiving
    task_id = tasks.task_manager().create_task(
        tasks.TaskType.SEND_AND_ARCHIVE,
        {"company_id": company.company_id},
    )

    # Set archived_at and reply_sent_at status fields
    current_time = datetime.datetime.now(datetime.timezone.utc)
    company.status.archived_at = current_time
    company.status.reply_sent_at = current_time
    models.company_repository().update(company)

    logger.info(f"Send and archive requested for {company.name}, task_id: {task_id}")

    return {
        "task_id": task_id,
        "status": tasks.TaskStatus.PENDING.value,
        "sent_at": current_time.isoformat(),
        "archived_at": current_time.isoformat(),
    }


# Remove the old ignore_and_archive handler function since frontend now uses message-centric endpoint


@view_config(route_name="archive_message_by_id", renderer="json", request_method="POST")
def archive_message_by_id(request):
    """Archive a specific message by message_id."""
    message_id = request.matchdict["message_id"]

    if not message_id:
        request.response.status = 400
        return {"error": "Message ID is required"}

    current_time = datetime.datetime.now(datetime.timezone.utc)
    repo = models.company_repository()

    # Get the message directly by ID
    message = repo.get_recruiter_message_by_id(message_id)

    if not message:
        request.response.status = 404
        return {"error": "Message not found"}

    # Set archived_at on the specific message
    message.archived_at = current_time
    repo.create_recruiter_message(message)  # This will update via upsert

    logger.info(f"Message {message_id} archived via direct endpoint")

    return {
        "message": "Message archived successfully",
        "message_id": message_id,
        "archived_at": current_time.isoformat(),
    }


@view_config(route_name="company_details", renderer="json", request_method="PATCH")
def patch_company_details(request) -> dict:
    company_id = request.matchdict["company_id"]
    company = models.company_repository().get(company_id)

    if not company:
        request.response.status = 404
        return {"error": "Company not found"}

    try:
        body = request.json_body
    except json.JSONDecodeError:
        request.response.status = 400
        return {"error": "Invalid JSON"}

    for key, value in body.items():
        setattr(company.details, key, value)

    models.company_repository().update(company)

    logger.info(f"Updated fields for {company.name}: {body}")
    company_dict = models.serialize_company(company)
    return company_dict["details"]


@view_config(route_name="companies", renderer="json", request_method="POST")
def research_by_url_or_name(request):
    """Start research for a company based on URL or name."""
    try:
        body = request.json_body
        company_url = body.get("url", "").strip()
        company_name = body.get("name", "").strip()

        if not company_url and not company_name:
            request.response.status = 400
            return {"error": "Either company URL or name must be provided"}

        # Create a new task
        task_args = {}
        if company_url:
            task_args["company_url"] = company_url
        if company_name:
            task_args["company_name"] = company_name

        task_id = tasks.task_manager().create_task(
            tasks.TaskType.COMPANY_RESEARCH,
            task_args,
        )
        logger.info(
            f"Research requested for company with URL: {company_url}, name: {company_name}, task_id: {task_id}"
        )

        return {
            "task_id": task_id,
            "status": tasks.TaskStatus.PENDING.value,
        }
    except Exception as e:
        logger.exception("Error creating company research task")
        request.response.status = 500
        return {"error": str(e)}


@view_config(route_name="import_companies", renderer="json", request_method="POST")
def import_companies_from_spreadsheet(request):
    """Start a task to import companies from the spreadsheet."""
    try:
        # No special arguments needed for this task
        task_args = {}

        # Optional parameters could be added here in the future

        task_id = tasks.task_manager().create_task(
            tasks.TaskType.IMPORT_COMPANIES_FROM_SPREADSHEET,
            task_args,
        )
        logger.info(f"Spreadsheet import requested, task_id: {task_id}")

        return {
            "task_id": task_id,
            "status": tasks.TaskStatus.PENDING.value,
        }
    except Exception as e:
        logger.exception("Error creating spreadsheet import task")
        request.response.status = 500
        return {"error": str(e)}


def main(global_config, **settings):
    with Configurator(settings=settings) as config:
        # Enable debugtoolbar for development
        config.include("pyramid_debugtoolbar")

        # Static files configuration
        here = os.path.dirname(os.path.abspath(__file__))
        static_path = os.path.join(here, "static")

        # Create static directory if it doesn't exist
        if not os.path.exists(static_path):
            os.makedirs(static_path)

        # Routes
        config.add_route("home", "/")
        config.add_route("companies", "/api/companies")
        config.add_route("messages", "/api/messages")
        config.add_route("research", "/api/companies/{company_id}/research")
        config.add_route("message_reply", "/api/messages/{message_id}/reply")
        config.add_route(
            "send_and_archive", "/api/companies/{company_id}/send_and_archive"
        )
        config.add_route(
            "send_and_archive_message", "/api/messages/{message_id}/send_and_archive"
        )
        # Remove the old ignore_and_archive route since frontend now uses message-centric endpoint
        config.add_route("company_details", "/api/companies/{company_id}/details")
        config.add_route("company", "/api/companies/{company_id}")
        config.add_route("scan_recruiter_emails", "/api/scan_recruiter_emails")
        config.add_route("task_status", "/api/tasks/{task_id}")
        config.add_route("import_companies", "/api/import_companies")
        config.add_route("archive_message_by_id", "/api/messages/{message_id}/archive")
        config.add_static_view(name="static", path="static")
        config.scan()

        setup_logging(process_name="server")
        setup_colored_logging()

        # Initialize repository
        models.company_repository()

        # Configure JSON renderer to use our custom encoder
        config.add_renderer(
            "json",
            JSON(serializer=lambda v, **kw: json.dumps(v, cls=models.CustomJSONEncoder)),
        )

        return config.make_wsgi_app()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(os.path.dirname(here), "development.ini")
    if not os.path.exists(config_file):
        raise Exception(f"Config file not found at {config_file}")

    cmd = PServeCommand(["pserve", config_file])
    cmd.run()
