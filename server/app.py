import json
import logging
import os
from datetime import datetime

import colorama
from colorama import Fore, Style
from pyramid.config import Configurator
from pyramid.renderers import JSON
from pyramid.response import Response
from pyramid.scripts.pserve import PServeCommand
from pyramid.view import view_config

import models
import tasks


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
    # Remove any existing handlers
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    # Add our handler
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


# Get our application logger
logger = logging.getLogger(__name__)


@view_config(route_name="company", renderer="json", request_method="GET")
def get_company(request) -> dict:
    company_name = request.matchdict["company_name"]
    repo = models.company_repository()
    company = repo.get(company_name)

    if not company:
        request.response.status = 404
        return {"error": "Company not found"}

    company_dict = get_company_dict_with_status(company, repo)
    return company_dict


def get_company_dict_with_status(
    company: models.Company, repo: models.CompanyRepository
) -> dict:
    company_dict = models.serialize_company(company)

    # Get the latest reply_sent event for this company
    reply_events = repo.get_events(
        company_name=company.name, event_type=models.EventType.REPLY_SENT
    )
    if reply_events:
        company_dict["sent_at"] = reply_events[0].timestamp

    # Get the latest research_completed event for this company
    research_events = repo.get_events(
        company_name=company.name, event_type=models.EventType.RESEARCH_COMPLETED
    )
    if research_events:
        company_dict["research_completed_at"] = research_events[0].timestamp
        company_dict["research_status"] = "completed"

    # Format research errors as a readable string to avoid [object Object] display
    if (
        company.details
        and hasattr(company.details, "research_errors")
        and company.details.research_errors
    ):
        formatted_errors = []
        for err in company.details.research_errors:
            formatted_errors.append(f"{err.step}: {err.error}")
        company_dict["research_errors"] = "; ".join(formatted_errors)

    research_errors = repo.get_events(
        company_name=company.name, event_type=models.EventType.RESEARCH_ERROR
    )
    if research_errors:
        company_dict["research_error_at"] = research_errors[0].timestamp
        if (
            research_events
            and research_events[0].timestamp > research_errors[0].timestamp
        ):
            company_dict["research_status"] = "completed"
        else:
            company_dict["research_status"] = "error"

    return company_dict


@view_config(route_name="companies", renderer="json", request_method="GET")
def get_companies(request) -> list[dict]:
    repo = models.company_repository()
    companies = repo.get_all(include_messages=True)

    company_data = []
    for company in companies:
        company_dict = get_company_dict_with_status(company, repo)
        company_data.append(company_dict)

    return company_data


@view_config(route_name="home")
def home(request):
    # Read and return the index.html file
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'static', 'index.html')) as f:
        return Response(f.read(), content_type="text/html")


def create_stub_message(company_name: str) -> str:
    return f"generated reply {company_name} {datetime.now().isoformat()}"


@view_config(route_name="generate_message", renderer="json", request_method="POST")
def generate_message(request):
    company_name = request.matchdict["company_name"]
    company = models.company_repository().get(company_name)
    if company is None:
        request.response.status = 404
        return {"error": "Company not found"}
    if not company.recruiter_message:
        request.response.status = 400
        return {"error": "No recruiter message to reply to"}

    task_id = tasks.task_manager().create_task(
        tasks.TaskType.GENERATE_REPLY,
        {"company_name": company_name},
    )
    logger.info(f"Generate reply requested for {company_name}, task_id: {task_id}")

    return {"task_id": task_id, "status": tasks.TaskStatus.PENDING.value}


@view_config(route_name="generate_message", renderer="json", request_method="PUT")
def update_message(request):
    company_name = request.matchdict["company_name"]
    try:
        body = request.json_body
        message = body.get("message")
        if not message:
            request.response.status = 400
            return {"error": "Message is required"}

        company = models.company_repository().get(company_name)
        if not company:
            request.response.status = 404
            return {"error": "Company not found"}

        company.reply_message = message
        models.company_repository().update(company)

        logger.info(f"Updated message for {company_name}: {message}")
        return models.serialize_company(company)
    except json.JSONDecodeError:
        request.response.status = 400
        return {"error": "Invalid JSON"}


@view_config(route_name="research", renderer="json", request_method="POST")
def research_company(request):
    company_name = request.matchdict["company_name"]
    company = models.company_repository().get(company_name)

    if not company:
        request.response.status = 404
        return {"error": "Company not found"}

    # Create a new task
    task_id = tasks.task_manager().create_task(
        tasks.TaskType.COMPANY_RESEARCH,
        {"company_name": company_name},
    )
    logger.info(f"Research requested for {company_name}, task_id: {task_id}")

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

    return task


@view_config(route_name="scan_recruiter_emails", renderer="json", request_method="POST")
def scan_recruiter_emails(request):
    max_messages = request.json_body.get("max_messages", 10)
    do_research = request.json_body.get("do_research", False)
    task_id = tasks.task_manager().create_task(
        tasks.TaskType.FIND_COMPANIES_FROM_RECRUITER_MESSAGES,
        {"max_messages": max_messages, "do_research": do_research},
    )
    logger.info(f"Email scan requested with do_research={do_research}, task_id: {task_id}")
    return {"task_id": task_id, "status": tasks.TaskStatus.PENDING.value}


@view_config(route_name="send_and_archive", renderer="json", request_method="POST")
def send_and_archive(request):
    company_name = request.matchdict["company_name"]
    company = models.company_repository().get(company_name)

    if not company:
        request.response.status = 404
        return {"error": "Company not found"}

    if not company.reply_message:
        request.response.status = 400
        return {"error": "No reply message to send"}

    # Create a new task for sending and archiving
    task_id = tasks.task_manager().create_task(
        tasks.TaskType.SEND_AND_ARCHIVE,
        {"company_name": company_name},
    )
    logger.info(f"Send and archive requested for {company_name}, task_id: {task_id}")

    # Add the current time as sent_at
    sent_at = datetime.now().isoformat()

    return {
        "task_id": task_id, 
        "status": tasks.TaskStatus.PENDING.value,
        "sent_at": sent_at
    }


@view_config(route_name="ignore_and_archive", renderer="json", request_method="POST")
def ignore_and_archive(request):
    company_name = request.matchdict["company_name"]
    company = models.company_repository().get(company_name)

    if not company:
        request.response.status = 404
        return {"error": "Company not found"}

    # Create a new task for just archiving (no reply sent)
    task_id = tasks.task_manager().create_task(
        tasks.TaskType.IGNORE_AND_ARCHIVE,
        {"company_name": company_name},
    )
    logger.info(f"Ignore and archive requested for {company_name}, task_id: {task_id}")

    return {
        "task_id": task_id,
        "status": tasks.TaskStatus.PENDING.value,
    }


def main(global_config, **settings):
    with Configurator(settings=settings) as config:
        # Enable debugtoolbar for development
        config.include("pyramid_debugtoolbar")

        # Static files configuration
        here = os.path.dirname(os.path.abspath(__file__))
        static_path = os.path.join(here, 'static')

        # Create static directory if it doesn't exist
        if not os.path.exists(static_path):
            os.makedirs(static_path)

        # Routes
        config.add_route('home', '/')
        config.add_route('companies', '/api/companies')
        config.add_route("company", "/api/companies/{company_name}")
        config.add_route(
            "generate_message", "/api/companies/{company_name}/reply_message"
        )
        config.add_route("research", "/api/companies/{company_name}/research")
        config.add_route("scan_recruiter_emails", "/api/scan_recruiter_emails")
        config.add_route(
            "send_and_archive", "/api/companies/{company_name}/send_and_archive"
        )
        config.add_route(
            "ignore_and_archive", "/api/companies/{company_name}/ignore_and_archive"
        )
        config.add_route("task_status", "/api/tasks/{task_id}")
        config.add_static_view(name='static', path='static')
        config.scan()

        setup_colored_logging()

        # Initialize repository
        models.company_repository()

        # Configure JSON renderer to use our custom encoder
        config.add_renderer(
            "json",
            JSON(
                serializer=lambda v, **kw: json.dumps(v, cls=models.CustomJSONEncoder)
            ),
        )

        return config.make_wsgi_app()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(os.path.dirname(here), "development.ini")
    if not os.path.exists(config_file):
        raise Exception(f"Config file not found at {config_file}")

    cmd = PServeCommand(["pserve", config_file])
    cmd.run()
