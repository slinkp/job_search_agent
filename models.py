import argparse
import datetime
import decimal
import enum
import json
import logging
import multiprocessing
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, ClassVar, Iterator, List, Optional

import dateutil.parser
from pydantic import BaseModel, Field, ValidationError, model_validator
from slugify import slugify
from typing_extensions import Self


def normalize_company_name(name: str) -> str:
    """Normalize company name for consistent comparison and ID generation.

    Uses python-slugify to convert the name to a URL-friendly slug:
    - Converts to lowercase
    - Replaces spaces and special chars with hyphens
    - Removes non-alphanumeric chars
    - Collapses multiple hyphens
    - Replaces '&' with 'and'

    Args:
        name: The company name to normalize

    Returns:
        The normalized company name as a slug
    """
    replacements = [["&", "and"]]
    return slugify(name.strip(), replacements=replacements)


def is_placeholder(name: str | None) -> bool:
    """Return True if name should be replaced with pretty much any other name"""
    if name is None:
        return True
    name = name.strip().lower()
    if not name:
        return True
    if name.startswith("company from"):
        return True
    if name.startswith("<unknown"):
        return True
    if name in ("unknown", "placeholder"):
        return True
    return False


class EventType(enum.Enum):
    REPLY_SENT = "reply_sent"
    RESEARCH_COMPLETED = "research_completed"
    COMPANY_CREATED = "company_created"
    COMPANY_UPDATED = "company_updated"
    RESEARCH_ERROR = "research_error"
    ARCHIVED = "archived"
    STATUS_CHANGED = "status_changed"
    FIT_DECISION = "fit_decision"


class ResearchStepError(BaseModel):
    """Error information for a research step that failed."""

    step: str
    error: str
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class Event(BaseModel):

    id: Optional[int] = None
    company_id: str
    event_type: EventType
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    details: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> dict:
        if isinstance(data, dict):
            # Convert string event_type to enum if needed
            if isinstance(data.get("event_type"), str):
                try:
                    data["event_type"] = EventType(data["event_type"])
                except ValueError:
                    pass

            # Parse timestamp string to datetime if needed
            if isinstance(data.get("timestamp"), str):
                try:
                    data["timestamp"] = dateutil.parser.parse(data["timestamp"])
                except ValueError:
                    pass
        return data


logger = logging.getLogger(__name__)

DEFAULT_CURRENT_STATE = "25. consider applying"


class BaseSheetRow(BaseModel):
    """Base class for spreadsheet rows."""

    # Default values, subclasses should override

    # I can feel it, filling columns down and right, oh lord
    fill_columns: ClassVar[tuple[str, ...]] = tuple()
    sort_by_date_field: ClassVar[str] = ""

    model_config = {
        "from_attributes": True,
        "str_strip_whitespace": True,
        "coerce_numbers_to_str": False,
    }

    @model_validator(mode="before")
    @classmethod
    def normalize_base_fields(cls, data: Any) -> dict:
        """Pre-process fields before Pydantic validation"""
        if isinstance(data, dict):
            for field_name, field in cls.model_fields.items():
                # First ensure all fields exist with defaults
                # (this prevents attribute errors when loading from eg old pickles that are missing fields)  # noqa: B950
                if field_name not in data:
                    data[field_name] = field.default

                # Then process type conversions.
                # Hacky, is there a better way to handle eg Optional[date]?
                val = data.get(field_name)
                if "date" in str(field.annotation) and isinstance(val, str):
                    try:
                        data[field_name] = dateutil.parser.parse(data[field_name])
                    except (ValueError, ValidationError):
                        # TODO: only do this if optional
                        data[field_name] = None
                elif "bool" in str(field.annotation) and isinstance(val, str):
                    data[field_name] = (
                        val.strip().strip().lower() == "yes" if val else None
                    )
                elif "int" in str(field.annotation) and isinstance(val, str):
                    val = val.strip().replace(",", "")
                    val = val.split(".")[0]
                    data[field_name] = int(val) if val else None
                elif "Decimal" in str(field.annotation) and isinstance(val, str):
                    try:
                        data[field_name] = decimal.Decimal(val)
                    except decimal.InvalidOperation:
                        # TODO: only do this if optional
                        data[field_name] = None
        return data

    @classmethod
    def sort_by_date_index(cls) -> int:
        return cls.field_index(cls.sort_by_date_field)

    @classmethod
    def is_filled_col_index(cls, col_index: int) -> bool:
        """Check if a column should be filled down"""
        for fieldname in cls.fill_columns:
            if col_index == cls.field_index(fieldname):
                return True
        return False

    @classmethod
    def field_index(cls, field_name: str) -> int:
        """Get the index of a field in the row"""
        try:
            return list(cls.model_fields.keys()).index(field_name)
        except ValueError:
            raise ValueError(f"Field {field_name} not found")

    @classmethod
    def field_name(cls, index: int) -> str:
        """Get the name of a field by its index"""
        try:
            return list(cls.model_fields.keys())[index]
        except IndexError:
            raise IndexError(f"Field index {index} out of range")

    def iter_to_strs(self) -> Iterator[str]:
        """Iterate through fields as strings"""
        for field_name in self.__class__.model_fields.keys():
            value = getattr(self, field_name)
            yield str(value) if value is not None else ""

    def as_list_of_str(self) -> list[str]:
        """Convert row back to list of strings"""
        return list(self.iter_to_strs())

    def __len__(self) -> int:
        """Return the number of fields in the row"""
        return len(self.__class__.model_fields)

    def __str__(self) -> str:
        """Custom string representation showing only non-default values"""
        cls_name = self.__class__.__name__
        fields = []
        for name, field in self.__class__.model_fields.items():
            value = getattr(self, name)
            default = field.default
            if value != default:
                fields.append(f"{name}={value}")
        if fields:
            return f"{cls_name}({', '.join(fields)})"
        return f"{cls_name}()"

    @classmethod
    def fill_column_indices(cls) -> list[int]:
        """Get indices of columns that should be filled down"""
        return [
            idx
            for idx, field_name in enumerate(cls.model_fields)
            if field_name in cls.fill_columns
        ]

    @classmethod
    def from_list(cls, row_data: list[str]) -> "BaseSheetRow":
        """Convert a list of strings into a row instance"""
        field_names = [name for name in cls.model_fields.keys()]

        # Create a dictionary with default values for fields
        data = {}
        for name, field in cls.model_fields.items():
            # Use default values for fields that expect lists or other complex types
            if "List" in str(field.annotation) or "list" in str(field.annotation):
                data[name] = (
                    field.default_factory() if field.default_factory is not None else []  # type: ignore
                )
            else:
                # Handle None default values
                if field.default is None:
                    data[name] = None
                else:
                    data[name] = field.default

        # Update with values from row_data
        for name, value in zip(field_names, row_data):
            # Skip updating list fields with empty strings
            if value != "" or (
                "List" not in str(cls.model_fields[name].annotation)
                and "list" not in str(cls.model_fields[name].annotation)
            ):
                data[name] = value

        return cls(**data)


class CompaniesSheetRow(BaseSheetRow):
    """
    Schema for the companies spreadsheet.
    Note, order of fields determines index of column in sheet!

    Also usable as a validated data model for company info.
    """

    name: Optional[str] = Field(default="")
    type: Optional[str] = Field(default="")
    valuation: Optional[str] = Field(default="")
    funding_series: Optional[str] = Field(default="")
    rc: Optional[bool] = Field(default=None)
    url: Optional[str] = Field(default="")

    current_state: Optional[str] = Field(
        default=DEFAULT_CURRENT_STATE
    )  # TODO validate other values
    updated: Optional[datetime.date | datetime.datetime] = Field(default=None)

    started: Optional[datetime.date] = Field(default=None)
    latest_step: Optional[str] = Field(default=None)
    next_step: Optional[str] = Field(default=None)
    next_step_date: Optional[datetime.date] = Field(default=None)
    latest_contact: Optional[str] = Field(default=None)

    end_date: Optional[datetime.date] = Field(default=None)

    maybe_referrals: Optional[str] = Field(default=None)
    referral_name: Optional[str] = Field(default=None)
    recruit_contact: Optional[str] = Field(default=None)

    total_comp: Optional[decimal.Decimal] = Field(default=None)
    base: Optional[decimal.Decimal] = Field(default=None)
    rsu: Optional[decimal.Decimal] = Field(default=None)
    bonus: Optional[decimal.Decimal] = Field(default=None)
    vesting: Optional[str] = Field(default=None)
    level_equiv: Optional[str] = Field(default=None)

    leetcode: Optional[bool] = Field(default=None)
    sys_design: Optional[bool] = Field(default=None)

    ai_notes: Optional[str] = Field(default=None)

    remote_policy: Optional[str] = Field(default=None)  # TODO validate values
    eng_size: Optional[int] = Field(default=None)
    total_size: Optional[int] = Field(default=None)
    headquarters: Optional[str] = Field(default=None)
    ny_address: Optional[str] = Field(default=None)
    commute_home: Optional[str] = Field(default=None)
    commute_lynn: Optional[str] = Field(default=None)

    notes: Optional[str] = Field(default=None)

    email_thread_link: Optional[str] = Field(default="")
    message_id: Optional[str] = Field(default="")

    promising: Optional[bool] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> dict:
        """Normalize fields that require validation"""
        if isinstance(data, dict) and "cleared" in data:
            cleared = data["cleared"]
            if isinstance(cleared, (bool, type(None))):
                data["cleared"] = "yes" if cleared else ""
            elif cleared and str(cleared).strip().lower() == "yes":
                data["cleared"] = "yes"
            else:
                data["cleared"] = ""
        return data

    fill_columns: ClassVar[tuple[str, ...]] = ()
    sort_by_date_field: ClassVar[str] = "updated"

    @property
    def company_identifier(self) -> str:
        if self.name and self.url:
            return f"{self.name} at {self.url}"
        elif self.name:
            return self.name
        elif self.url:
            return f"with unknown name at {self.url}"
        return ""


class RecruiterMessage(BaseModel):
    """
    Represents a recruiter message with its content and metadata.

    Attributes:
        message_id: Unique Gmail message ID for this specific message
        company_id: ID of the company this message is associated with
        message: The content of the message
        subject: Email subject line
        sender: Email sender (recruiter's email address)
        email_thread_link: URL to the email thread in Gmail
        thread_id: Gmail thread ID
        date: Timestamp of the message as UTC datetime
        archived_at: When this specific message was archived (optional)
        reply_sent_at: When a reply was sent to this message (optional)
    """

    @property
    def is_archived(self) -> bool:
        """True if either message is archived or company is archived."""
        # Company check will be implemented in repository queries
        return self.archived_at is not None

    message_id: str = ""
    company_id: str = ""
    message: str = ""
    subject: Optional[str] = ""
    sender: Optional[str] = ""
    email_thread_link: str = ""
    thread_id: str = ""
    date: Optional[datetime.datetime] = None
    archived_at: Optional[datetime.datetime] = None
    reply_sent_at: Optional[datetime.datetime] = None


class FitCategory(str, enum.Enum):
    """Categories for company fit decisions."""

    GOOD = "good"
    BAD = "bad"
    NEEDS_MORE_INFO = "needs_more_info"


class CompanyStatus(BaseModel):
    """Status and metadata about our interaction with a company."""

    research_errors: List[ResearchStepError] = Field(default_factory=list)
    research_failed_at: Optional[datetime.datetime] = None
    research_completed_at: Optional[datetime.datetime] = None
    archived_at: Optional[datetime.datetime] = None
    reply_sent_at: Optional[datetime.datetime] = None  # When we sent a reply
    imported_from_spreadsheet: bool = (
        False  # Whether this company was imported from spreadsheet
    )
    imported_at: Optional[datetime.datetime] = (
        None  # When the company was imported from spreadsheet
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # Company fit decision fields
    fit_category: Optional[FitCategory] = Field(
        default=None, description="Whether this company is a good fit"
    )
    fit_confidence_score: Optional[float] = Field(
        default=None,
        description="Confidence score for the fit decision (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    fit_decision_timestamp: Optional[datetime.datetime] = Field(
        default=None, description="When the fit decision was made"
    )
    fit_features_used: List[str] = Field(
        default_factory=list,
        description="List of feature names used in making the fit decision",
    )

    @model_validator(mode="after")
    def validate_fit_decision(self) -> Self:
        """Validate that fit decision fields are consistent."""
        if self.fit_category is not None:
            if self.fit_confidence_score is None:
                raise ValueError(
                    "fit_confidence_score is required when fit_category is set"
                )
            if self.fit_decision_timestamp is None:
                raise ValueError(
                    "fit_decision_timestamp is required when fit_category is set"
                )
        return self

    @property
    def research_status(self) -> str:
        if self.research_completed_at and not self.research_failed_at:
            return "completed"
        if self.research_failed_at and not self.research_completed_at:
            return "failed"
        if self.research_failed_at and self.research_completed_at:
            if self.research_completed_at > self.research_failed_at:
                return "completed"
            else:
                return "failed"
        return "none"

    @property
    def has_fit_decision(self) -> bool:
        """Return True if a fit decision has been made for this company."""
        return self.fit_category is not None and self.fit_decision_timestamp is not None


class Company(BaseModel):
    company_id: str
    name: str
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    # Tracks last meaningful business activity timestamp (separate from updated_at)
    activity_at: Optional[datetime.datetime] = None
    # Human-readable description of the last meaningful activity (e.g. "message received", "reply sent")
    last_activity: Optional[str] = None
    details: CompaniesSheetRow
    status: CompanyStatus = Field(default_factory=CompanyStatus)
    reply_message: str = ""
    recruiter_message: Optional[RecruiterMessage] = None

    @property
    def message_id(self) -> Optional[str]:
        """Get the message_id from the recruiter_message if it exists."""
        if self.recruiter_message is None:
            return None
        return self.recruiter_message.message_id

    @property
    def email_thread_link(self) -> str:
        if self.recruiter_message is None:
            return ""
        return self.recruiter_message.email_thread_link or ""

    @property
    def thread_id(self) -> str:
        if self.recruiter_message is None:
            return ""
        return self.recruiter_message.thread_id or ""

    @property
    def initial_message(self) -> str:
        if self.recruiter_message is None:
            return ""
        return self.recruiter_message.message or ""

    @initial_message.setter
    def initial_message(self, message: str):
        if self.recruiter_message is None:
            # Create a minimal RecruiterMessage if none exists
            self.recruiter_message = RecruiterMessage(
                message=message, company_id=self.company_id
            )
        else:
            self.recruiter_message.message = message

    @property
    def messages(self) -> List[RecruiterMessage]:
        """Get all recruiter messages for this company."""
        return company_repository().get_recruiter_messages(self.company_id)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        if isinstance(obj, enum.Enum):
            return obj.value
        if isinstance(obj, EventType):
            return obj.value
        if isinstance(obj, (Event, CompanyStatus)):
            return obj.model_dump()
        if isinstance(obj, ResearchStepError):
            return {
                "step": obj.step,
                "error": obj.error,
                "timestamp": obj.timestamp.isoformat() if obj.timestamp else None,
            }
        if isinstance(obj, Company):
            return serialize_company(obj)
        return super().default(obj)


class CompanyRepository:

    def __init__(
        self,
        db_path: str = "data/companies.db",
        load_sample_data: bool = False,
        clear_data: bool = False,
    ):
        self.db_path = db_path
        self.lock = multiprocessing.Lock()
        self._ensure_db_dir()
        self._init_db(load_sample_data, clear_data)

    def _ensure_db_dir(self):
        """Ensure the database directory exists."""
        # Skip directory creation for in-memory databases
        if self.db_path == ":memory:":
            return
        db_dir = os.path.dirname(self.db_path)
        if db_dir:  # Only create directory if there's a directory part
            os.makedirs(db_dir, exist_ok=True)

    def _init_db(self, load_sample_data: bool, clear_data: bool):
        with self.lock:
            with self._get_connection() as conn:
                if clear_data:
                    conn.execute("DROP TABLE IF EXISTS companies")
                    conn.execute("DROP TABLE IF EXISTS recruiter_messages")
                    conn.execute("DROP TABLE IF EXISTS events")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS companies (
                        company_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                        details TEXT NOT NULL DEFAULT '{}',
                        status TEXT NOT NULL DEFAULT '{}',  -- New status column with default empty JSON
                        activity_at TEXT DEFAULT NULL,
                        last_activity TEXT DEFAULT NULL,
                        reply_message TEXT,
                        deleted_at TEXT DEFAULT NULL
                    )
                """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS recruiter_messages (
                        message_id TEXT PRIMARY KEY,
                        company_id TEXT NOT NULL,
                        subject TEXT DEFAULT '',
                        sender TEXT DEFAULT '',
                        message TEXT DEFAULT '',
                        thread_id TEXT NOT NULL,
                        email_thread_link TEXT DEFAULT '',
                        date TEXT DEFAULT '',
                        archived_at TEXT DEFAULT '',
                        reply_sent_at TEXT DEFAULT '',
                        FOREIGN KEY (company_id) REFERENCES companies (company_id)
                    )
                """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                        details TEXT,
                        FOREIGN KEY (company_id) REFERENCES companies (company_id)
                    )
                """
                )
                # Aliases table (first-class model for name variations)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS company_aliases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id TEXT NOT NULL,
                        alias TEXT NOT NULL,
                        normalized_alias TEXT NOT NULL,
                        source TEXT NOT NULL DEFAULT 'auto',
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                        FOREIGN KEY (company_id) REFERENCES companies (company_id)
                    )
                    """
                )
                # Indexes to enforce uniqueness for active aliases and support lookups
                conn.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_company_aliases_company_norm_active
                    ON company_aliases(company_id, normalized_alias)
                    WHERE is_active = 1
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_company_aliases_normalized_alias
                    ON company_aliases(normalized_alias)
                    WHERE is_active = 1
                    """
                )
        if load_sample_data:
            for company in SAMPLE_COMPANIES:
                self.create(company)

    @contextmanager
    def _get_connection(self):
        # Create a new connection each time, don't store in thread local
        connection = sqlite3.connect(self.db_path, timeout=60.0)
        try:
            yield connection
        finally:
            connection.close()

    def get(self, company_id: str, include_aliases=False) -> Optional[Company]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT company_id, name, updated_at, details, status, activity_at, last_activity, reply_message FROM companies WHERE company_id = ?",
                (company_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            company = self._deserialize_company(row)

            # Always fetch recruiter message
            message = self._get_recruiter_message(company_id, conn)
            company.recruiter_message = message

            if include_aliases:
                # Fetch aliases for this company
                cursor = conn.execute(
                    """
                    SELECT alias, source, is_active
                    FROM company_aliases
                    WHERE company_id = ?
                    ORDER BY source, alias
                    """,
                    (company_id,),
                )
                aliases = [
                    {
                        "alias": row[0],
                        "source": row[1],
                        "is_active": bool(row[2]),
                    }
                    for row in cursor.fetchall()
                ]
                object.__setattr__(company, "_aliases", aliases)

            return company

    def soft_delete_company(self, company_id: str) -> bool:
        """
        Soft delete a company by setting its deleted_at timestamp.

        Args:
            company_id: The ID of the company to soft delete

        Returns:
            True if the company was successfully soft deleted, False if it doesn't exist
        """
        with self.lock:
            with self._get_connection() as conn:
                # Check if company exists and is not already deleted
                cursor = conn.execute(
                    "SELECT deleted_at FROM companies WHERE company_id = ?", (company_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return False  # Company doesn't exist

                if row[0] is not None:
                    return True  # Company is already deleted. Idempotent.

                # Soft delete the company
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                conn.execute(
                    "UPDATE companies SET deleted_at = ? WHERE company_id = ?",
                    (now, company_id),
                )
                conn.commit()
                return True

    def get_recruiter_message(self, company_id: str) -> Optional[RecruiterMessage]:
        """
        Get a single recruiter message by company id.
        """
        with self._get_connection() as conn:
            return self._get_recruiter_message(company_id, conn)

    def get_recruiter_messages(self, company_id: str) -> List[RecruiterMessage]:
        """
        Get all recruiter messages for a company.
        """
        with self._get_connection() as conn:
            return self._get_recruiter_messages(company_id, conn)

    def get_recruiter_message_by_id(self, message_id: str) -> Optional[RecruiterMessage]:
        """
        Get a recruiter message by its message_id.
        """
        with self._get_connection() as conn:
            return self._get_recruiter_message_by_id(message_id, conn)

    def _get_recruiter_messages(
        self, company_id: str, conn: sqlite3.Connection
    ) -> List[RecruiterMessage]:
        """Get all recruiter messages for a company from the database."""
        cursor = conn.execute(
            "SELECT message_id, company_id, subject, sender, message, thread_id, email_thread_link, date, archived_at FROM recruiter_messages WHERE company_id = ? ORDER BY date DESC",
            (company_id,),
        )
        messages = []
        for row in cursor.fetchall():
            # Parse the date string to datetime if it exists
            date_str = row[7]
            archived_at_str = row[8]
            date = None
            archived_at = None
            if date_str:
                try:
                    date = dateutil.parser.parse(date_str).replace(
                        tzinfo=datetime.timezone.utc
                    )
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse date string: {date_str}")
            if archived_at_str:
                try:
                    archived_at = dateutil.parser.parse(archived_at_str).replace(
                        tzinfo=datetime.timezone.utc
                    )
                except (ValueError, TypeError):
                    logger.warning(
                        f"Failed to parse archived_at string: {archived_at_str}"
                    )

            recruiter_message = RecruiterMessage(
                message_id=row[0],
                company_id=row[1],
                subject=row[2],
                sender=row[3],
                message=row[4],
                thread_id=row[5],
                email_thread_link=row[6],
                date=date,
                archived_at=archived_at,
            )
            messages.append(recruiter_message)
        return messages

    def _get_recruiter_message_by_id(
        self, message_id: str, conn: sqlite3.Connection
    ) -> Optional[RecruiterMessage]:
        """Get a recruiter message by its message_id from the database."""
        cursor = conn.execute(
            "SELECT message_id, company_id, subject, sender, message, thread_id, email_thread_link, date, archived_at, reply_sent_at FROM recruiter_messages WHERE message_id = ?",
            (message_id,),
        )
        row = cursor.fetchone()
        if row:
            # Parse the date string to datetime if it exists
            date_str = row[7]
            archived_at_str = row[8]
            reply_sent_at_str = row[9]
            date = None
            archived_at = None
            reply_sent_at = None
            if date_str:
                try:
                    date = dateutil.parser.parse(date_str).replace(
                        tzinfo=datetime.timezone.utc
                    )
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse date string: {date_str}")
            if archived_at_str:
                try:
                    archived_at = dateutil.parser.parse(archived_at_str).replace(
                        tzinfo=datetime.timezone.utc
                    )
                except (ValueError, TypeError):
                    logger.warning(
                        f"Failed to parse archived_at string: {archived_at_str}"
                    )
            if reply_sent_at_str:
                try:
                    reply_sent_at = dateutil.parser.parse(reply_sent_at_str).replace(
                        tzinfo=datetime.timezone.utc
                    )
                except (ValueError, TypeError):
                    logger.warning(
                        f"Failed to parse reply_sent_at string: {reply_sent_at_str}"
                    )

            recruiter_message = RecruiterMessage(
                message_id=row[0],
                company_id=row[1],
                subject=row[2],
                sender=row[3],
                message=row[4],
                thread_id=row[5],
                email_thread_link=row[6],
                date=date,
                archived_at=archived_at,
                reply_sent_at=reply_sent_at,
            )
            return recruiter_message
        return None

    def get_by_normalized_name(
        self, name: str, include_deleted=False
    ) -> Optional[Company]:
        """
        Get a company by its normalized name (case-insensitive, whitespace-insensitive).

        Args:
            name: The company name to search for
            include_deleted: Whether to include soft-deleted companies in the search

        Returns:
            The Company if found, None otherwise
        """
        # First try to resolve via aliases (active only)
        alias_company_id = self.resolve_alias(name)
        if alias_company_id:
            return self.get(alias_company_id)

        normalized_name = normalize_company_name(name)

        with self._get_connection() as conn:
            # Query for companies where the normalized version of the name matches
            query = "SELECT company_id, name, updated_at, details, status, activity_at, last_activity, reply_message FROM companies"
            if not include_deleted:
                query += " WHERE deleted_at IS NULL"

            cursor = conn.execute(query)
            for row in cursor.fetchall():
                # We normalize each company name from the database and compare.
                # This is slow, but fine since we expect to have O(100) companies at most.
                company_id, db_name = row[0], row[1]
                if normalize_company_name(db_name) == normalized_name:
                    company = self._deserialize_company(row)
                    message = self._get_recruiter_message(company_id, conn)
                    company.recruiter_message = message
                    return company

        return None

    def resolve_alias(self, name: str) -> Optional[str]:
        """Resolve a name via company_aliases to a company_id if an active alias exists.

        Returns the matching company_id or None if no active alias matches.
        """
        normalized = normalize_company_name(name)
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT company_id FROM company_aliases WHERE normalized_alias = ? AND is_active = 1 LIMIT 1",
                (normalized,),
            ).fetchone()
            if row:
                return row[0]
        return None

    def create_alias(self, company_id: str, alias: str, source: str = "manual") -> int:
        """Create a new alias for a company.

        Args:
            company_id: The company ID
            alias: The alias name
            source: The source of the alias ("manual", "auto", "seed", "levels")

        Returns:
            The ID of the created alias

        Raises:
            sqlite3.IntegrityError: If the alias already exists for this company
        """
        normalized_alias = normalize_company_name(alias)
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO company_aliases (company_id, alias, normalized_alias, source, is_active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (company_id, alias, normalized_alias, source),
                )
                alias_id = cursor.lastrowid
                conn.commit()
                if alias_id is None:
                    raise RuntimeError("Failed to create alias - no ID returned")
                return alias_id

    def get_alias(self, alias_id: int) -> Optional[dict]:
        """Get an alias by its ID.

        Args:
            alias_id: The alias ID

        Returns:
            Dictionary with alias data or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, company_id, alias, normalized_alias, source, is_active, created_at, updated_at
                FROM company_aliases
                WHERE id = ?
                """,
                (alias_id,),
            ).fetchone()
            if row:
                return {
                    "id": row[0],
                    "company_id": row[1],
                    "alias": row[2],
                    "normalized_alias": row[3],
                    "source": row[4],
                    "is_active": bool(row[5]),
                    "created_at": row[6],
                    "updated_at": row[7],
                }
        return None

    def update_alias(
        self, alias_id: int, alias: Optional[str] = None, is_active: Optional[bool] = None
    ) -> Optional[dict]:
        """Update an alias.

        Args:
            alias_id: The alias ID
            alias: New alias name (optional)
            is_active: New active status (optional)

        Returns:
            Updated alias data or None if not found
        """
        with self.lock:
            with self._get_connection() as conn:
                # Check if alias exists
                existing = conn.execute(
                    "SELECT id FROM company_aliases WHERE id = ?",
                    (alias_id,),
                ).fetchone()
                if not existing:
                    return None

                # Build update query
                updates = []
                params = []

                if alias is not None:
                    updates.append("alias = ?")
                    updates.append("normalized_alias = ?")
                    params.extend([alias, normalize_company_name(alias)])

                if is_active is not None:
                    updates.append("is_active = ?")
                    params.append("1" if is_active else "0")

                if not updates:
                    return self.get_alias(alias_id)

                updates.append("updated_at = datetime('now')")
                params.append(str(alias_id))

                conn.execute(
                    f"UPDATE company_aliases SET {', '.join(updates)} WHERE id = ?",
                    params,
                )
                conn.commit()

                return self.get_alias(alias_id)

    def deactivate_alias(self, alias_id: int) -> bool:
        """Deactivate an alias by setting is_active to False.

        Args:
            alias_id: The alias ID

        Returns:
            True if alias was found and deactivated, False otherwise
        """
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE company_aliases
                    SET is_active = 0, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (alias_id,),
                )
                conn.commit()
                return cursor.rowcount > 0

    def list_aliases(self, company_id: str) -> list[dict]:
        """List all aliases for a company.

        Args:
            company_id: The company ID

        Returns:
            List of alias dictionaries with keys: id, alias, source, is_active
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, alias, source, is_active
                FROM company_aliases
                WHERE company_id = ?
                ORDER BY source, alias
                """,
                (company_id,),
            )
            return [
                {
                    "id": row[0],
                    "alias": row[1],
                    "source": row[2],
                    "is_active": bool(row[3]),
                }
                for row in cursor.fetchall()
            ]

    def set_alias_as_canonical(self, company_id: str, alias_id: int) -> bool:
        """Set an alias as the canonical name for a company.

        This updates the company's name and details.name, and preserves the old name
        as an alias if it's not already there.

        Args:
            company_id: The company ID
            alias_id: The alias ID to set as canonical

        Returns:
            True if successful, False if alias not found
        """
        with self.lock:
            with self._get_connection() as conn:
                # Get the alias
                alias_row = conn.execute(
                    """
                    SELECT alias, normalized_alias FROM company_aliases WHERE id = ? AND company_id = ?
                    """,
                    (alias_id, company_id),
                ).fetchone()
                if not alias_row:
                    return False

                alias_name, normalized_alias = alias_row

                # Get current company name
                company_row = conn.execute(
                    "SELECT name FROM companies WHERE company_id = ?",
                    (company_id,),
                ).fetchone()
                if not company_row:
                    return False

                old_name = company_row[0]
                old_normalized = normalize_company_name(old_name)

                # Update company name
                conn.execute(
                    "UPDATE companies SET name = ?, updated_at = datetime('now') WHERE company_id = ?",
                    (alias_name, company_id),
                )

                # Update company details if they exist
                details_row = conn.execute(
                    "SELECT details FROM companies WHERE company_id = ?",
                    (company_id,),
                ).fetchone()
                if details_row and details_row[0]:
                    try:
                        details = json.loads(details_row[0])
                        details["name"] = alias_name
                        conn.execute(
                            "UPDATE companies SET details = ? WHERE company_id = ?",
                            (json.dumps(details), company_id),
                        )
                    except (json.JSONDecodeError, KeyError):
                        # If details are malformed, just continue
                        pass

                # Preserve old name as alias if it's different and not already there
                if old_normalized != normalized_alias:
                    try:
                        conn.execute(
                            """
                            INSERT INTO company_aliases (company_id, alias, normalized_alias, source, is_active)
                            VALUES (?, ?, ?, 'seed', 1)
                            """,
                            (company_id, old_name, old_normalized),
                        )
                    except sqlite3.IntegrityError:
                        # Alias already exists, that's fine
                        pass

                conn.commit()
                return True

    def _get_recruiter_message(
        self, company_id: str, conn: sqlite3.Connection
    ) -> Optional[RecruiterMessage]:
        cursor = conn.execute(
            "SELECT message_id, company_id, subject, sender, message, thread_id, email_thread_link, date, archived_at FROM recruiter_messages WHERE company_id = ? ORDER BY date DESC",
            (company_id,),
        )
        row = cursor.fetchone()
        if row:  # noqa: B950
            # Parse the date string to datetime if it exists
            date_str = row[7]
            archived_at_str = row[8]
            date = None
            archived_at = None
            if date_str:
                try:
                    date = dateutil.parser.parse(date_str).replace(
                        tzinfo=datetime.timezone.utc
                    )
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse date string: {date_str}")
            if archived_at_str:
                try:
                    archived_at = dateutil.parser.parse(archived_at_str).replace(
                        tzinfo=datetime.timezone.utc
                    )
                except (ValueError, TypeError):
                    logger.warning(
                        f"Failed to parse archived_at string: {archived_at_str}"
                    )

            recruiter_message = RecruiterMessage(
                message_id=row[0],
                company_id=row[1],
                subject=row[2],
                sender=row[3],
                message=row[4],
                thread_id=row[5],
                email_thread_link=row[6],
                date=date,
                archived_at=archived_at,
            )
            return recruiter_message
        return None

    def create_recruiter_message(self, message: RecruiterMessage) -> None:
        with self.lock:
            with self._get_connection() as conn:
                self._upsert_recruiter_message(message, conn)
                conn.commit()

    def _upsert_recruiter_message(
        self, message: RecruiterMessage, conn: sqlite3.Connection
    ) -> None:
        """
        Insert or update a recruiter message.
        If a message with the same ID already exists, it will be updated.
        """
        # Convert datetime to ISO format string for SQLite storage
        date_str = message.date.isoformat() if message.date else ""
        archived_at_str = message.archived_at.isoformat() if message.archived_at else ""
        reply_sent_at_str = (
            message.reply_sent_at.isoformat() if message.reply_sent_at else ""
        )

        try:
            # Try to insert first
            conn.execute(
                """
                INSERT INTO recruiter_messages (
                    message_id, company_id, subject, sender, message, thread_id, email_thread_link, date, archived_at, reply_sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.company_id,
                    message.subject,  # noqa: B950
                    message.sender,
                    message.message,
                    message.thread_id,
                    message.email_thread_link,
                    date_str,
                    archived_at_str,
                    reply_sent_at_str,
                ),
            )
        except sqlite3.IntegrityError:
            # If it already exists, update it
            conn.execute(
                """
                UPDATE recruiter_messages
                SET company_id = ?, subject = ?, sender = ?, message = ?, thread_id = ?, email_thread_link = ?, date = ?, archived_at = ?, reply_sent_at = ?
                WHERE message_id = ?
                """,
                (
                    message.company_id,
                    message.subject,
                    message.sender,
                    message.message,
                    message.thread_id,
                    message.email_thread_link,
                    date_str,
                    archived_at_str,
                    reply_sent_at_str,
                    message.message_id,
                ),
            )

        # Update activity fields based on message state
        # Prefer reply_sent_at > archived_at > date
        if message.reply_sent_at:
            self._update_activity(
                conn, message.company_id, message.reply_sent_at, "reply sent"
            )
        elif message.archived_at:
            self._update_activity(
                conn, message.company_id, message.archived_at, "message archived"
            )
        elif message.date:
            self._update_activity(
                conn, message.company_id, message.date, "message received"
            )

    def get_all(
        self, include_messages=False, include_aliases=False, include_deleted=False
    ) -> List[Company]:
        # Reads can happen without the lock
        with self._get_connection() as conn:
            query = "SELECT company_id, name, updated_at, details, status, activity_at, last_activity, reply_message FROM companies"
            if not include_deleted:
                query += " WHERE deleted_at IS NULL"

            cursor = conn.execute(query)
            companies = [self._deserialize_company(row) for row in cursor.fetchall()]
            if include_messages:
                # Don't worry about this being slow for now
                for comp in companies:
                    message = self._get_recruiter_message(comp.company_id, conn)
                    comp.recruiter_message = message
            if include_aliases:
                # Add aliases to each company
                for comp in companies:
                    cursor = conn.execute(
                        """
                        SELECT alias, source, is_active
                        FROM company_aliases
                        WHERE company_id = ?
                        ORDER BY source, alias
                        """,
                        (comp.company_id,),
                    )
                    aliases = [
                        {
                            "alias": row[0],
                            "source": row[1],
                            "is_active": bool(row[2]),
                        }
                        for row in cursor.fetchall()
                    ]
                    # Store aliases as a private attribute on the company object
                    object.__setattr__(comp, "_aliases", aliases)
            return companies

    def _update_activity(
        self,
        conn: sqlite3.Connection,
        company_id: str,
        when: datetime.datetime,
        label: str,
    ) -> None:
        """Update a company's activity fields if the provided timestamp is newer.

        This is an internal helper that expects the caller to manage connection/transactions.
        """
        # Read current activity_at
        row = conn.execute(
            "SELECT activity_at FROM companies WHERE company_id = ?",
            (company_id,),
        ).fetchone()
        if row is None:
            return
        current_str = row[0]
        current_dt: Optional[datetime.datetime] = None
        if current_str:
            try:
                current_dt = dateutil.parser.parse(current_str)
            except Exception:
                current_dt = None

        if current_dt is None or when > current_dt:
            conn.execute(
                "UPDATE companies SET activity_at = ?, last_activity = ? WHERE company_id = ?",
                (when.isoformat(), label, company_id),
            )

    def update_activity(
        self,
        company_id: str,
        when: datetime.datetime,
        label: str,
    ) -> None:
        """Public method to update activity with locking and its own connection."""
        with self.lock:
            with self._get_connection() as conn:
                self._update_activity(conn, company_id, when, label)
                conn.commit()

    def get_all_messages(self, include_deleted=False) -> List[RecruiterMessage]:
        """Get all recruiter messages with basic company info."""
        # Reads can happen without the lock
        with self._get_connection() as conn:
            query = """
                SELECT m.message_id, m.company_id, m.message, m.subject, m.sender,
                       m.email_thread_link, m.thread_id, m.date, m.archived_at,
                       m.reply_sent_at, c.name as company_name, c.reply_message
                FROM recruiter_messages m
                LEFT JOIN companies c ON m.company_id = c.company_id
            """
            if not include_deleted:
                query += " WHERE c.deleted_at IS NULL"
            query += " ORDER BY m.date DESC"

            cursor = conn.execute(query)
            messages = []
            for row in cursor.fetchall():
                message = RecruiterMessage(
                    message_id=row[0],
                    company_id=row[1],
                    message=row[2],
                    subject=row[3],
                    sender=row[4],
                    email_thread_link=row[5],
                    thread_id=row[6],
                    date=dateutil.parser.parse(row[7]) if row[7] else None,
                    archived_at=dateutil.parser.parse(row[8]) if row[8] else None,
                    reply_sent_at=dateutil.parser.parse(row[9]) if row[9] else None,
                )
                # Store company name and reply message in a way that doesn't conflict with Pydantic
                # We'll use private attributes that can be accessed by the API layer
                object.__setattr__(message, "_company_name", row[10] or "Unknown Company")
                object.__setattr__(message, "_reply_message", row[11] or "")
                messages.append(message)
            return messages

    def create(self, company: Company) -> Company:
        with self.lock:
            with self._get_connection() as conn:
                try:
                    conn.execute(
                        """
                        INSERT INTO companies (
                            company_id, name, updated_at, details, status, reply_message
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            company.company_id,
                            company.name,
                            company.updated_at.isoformat(),
                            json.dumps(
                                company.details.model_dump(), cls=CustomJSONEncoder
                            ),
                            json.dumps(
                                company.status.model_dump(), cls=CustomJSONEncoder
                            ),
                            company.reply_message,
                        ),
                    )

                    # Save the recruiter message if it exists
                    if company.recruiter_message:
                        company.recruiter_message.company_id = company.company_id
                        self._upsert_recruiter_message(company.recruiter_message, conn)

                    conn.commit()
                    refreshed_company = self.get(
                        company.company_id
                    )  # To include generated timestamp
                    assert refreshed_company is not None
                    return refreshed_company
                except sqlite3.IntegrityError:
                    raise ValueError(f"Company {company.company_id} already exists")

    def update(self, company: Company) -> Company:
        # Sync top-level name with details.name if details.name is set
        # WARNING this assumes that company.details is latest and nothing
        # updates them the other way around :(
        if company.details and company.details.name:
            maybe_new_name = company.details.name.strip()
            old_name = (company.name or "").strip()
            if not old_name:
                logger.info(
                    f"Filling in empty company.name with company.details.name {maybe_new_name}"
                )
                company.name = maybe_new_name
            elif (
                old_name
                and not is_placeholder(maybe_new_name)
                and maybe_new_name != company.name
            ):
                company.name = maybe_new_name
                logger.info(
                    f"Clobbering company name {old_name} with company.details.name {maybe_new_name}"
                )
                company.name = company.details.name.strip()
            else:
                logger.info(
                    f"company.details.name {maybe_new_name} not a good replacement for {old_name}"
                )

        with self.lock:  # Lock for writes
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE companies
                    SET name = ?,
                        details = ?,
                        status = ?,
                        reply_message = ?,
                        updated_at = datetime('now')
                    WHERE company_id = ?
                    """,
                    (
                        company.name,
                        json.dumps(company.details.model_dump(), cls=CustomJSONEncoder),
                        json.dumps(company.status.model_dump(), cls=CustomJSONEncoder),
                        company.reply_message,
                        company.company_id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ValueError(f"Company {company.company_id} not found")

                # Update or create the recruiter message if it exists
                if company.recruiter_message:
                    company.recruiter_message.company_id = company.company_id
                    self._upsert_recruiter_message(company.recruiter_message, conn)

                conn.commit()
                refreshed_company = self.get(
                    company.company_id
                )  # To include generated timestamp
                assert refreshed_company is not None
                return refreshed_company

    def delete(self, company_id: str) -> None:
        with self.lock:  # Lock for writes
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM companies WHERE company_id = ?", (company_id,)
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Company {company_id} not found")
                conn.commit()

    def _deserialize_company(self, row: tuple) -> Company:
        """Convert a database row into a Company object."""
        assert row is not None
        # Support both old 6-column and new 8-column shape
        if len(row) == 6:
            company_id, name, updated_at, details_json, status_json, reply_message = row
            activity_at_str = None
            last_activity_str = None
        else:
            (
                company_id,
                name,
                updated_at,
                details_json,
                status_json,
                activity_at_str,
                last_activity_str,
                reply_message,
            ) = row
        details_dict = json.loads(details_json)

        # Parse the status JSON or use empty dict if NULL
        status_dict = json.loads(status_json) if status_json else {}

        # Parse updated_at as UTC timezone-aware datetime
        updated_at_dt = dateutil.parser.parse(updated_at).replace(
            tzinfo=datetime.timezone.utc
        )

        # Convert ISO format dates back to datetime.date
        for key, value in details_dict.items():
            if isinstance(value, str) and "date" in key:
                try:
                    details_dict[key] = dateutil.parser.parse(value).date()
                except (ValueError, TypeError):
                    details_dict[key] = None

        # Parse timestamps in status if they exist
        if "archived_at" in status_dict and status_dict["archived_at"]:
            try:
                status_dict["archived_at"] = dateutil.parser.parse(
                    status_dict["archived_at"]
                )
            except (ValueError, TypeError):
                status_dict["archived_at"] = None

        # Handle research errors
        if "research_errors" in details_dict:
            # Move research_errors from details to status for backward compatibility
            if "research_errors" not in status_dict:
                status_dict["research_errors"] = details_dict.pop("research_errors")

        activity_at_dt = None
        if activity_at_str:
            try:
                activity_at_dt = dateutil.parser.parse(activity_at_str).replace(
                    tzinfo=datetime.timezone.utc
                )
            except (ValueError, TypeError):
                activity_at_dt = None

        return Company(
            company_id=company_id,
            name=name,
            updated_at=updated_at_dt,
            activity_at=activity_at_dt,
            last_activity=last_activity_str if last_activity_str else None,
            details=CompaniesSheetRow(**details_dict),
            status=CompanyStatus(**status_dict),
            reply_message=reply_message,
        )

    def create_event(self, event: Event) -> Event:
        """Create a new event record"""
        if not event.timestamp:
            event.timestamp = datetime.datetime.now(datetime.timezone.utc)

        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO events (company_id, event_type, timestamp, details)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        event.company_id,
                        event.event_type.value,
                        event.timestamp.isoformat(),
                        event.details,
                    ),
                )
                conn.commit()
                event_id = cursor.lastrowid
                event.id = event_id
                return event

    def get_events(
        self, company_id: Optional[str] = None, event_type: Optional[EventType] = None
    ) -> List[Event]:
        """Get events, optionally filtered by company id and/or event type"""
        query = "SELECT id, company_id, event_type, timestamp, details FROM events"
        params = []

        if company_id or event_type:
            query += " WHERE"

            if company_id:
                query += " company_id = ?"
                params.append(company_id)

            if event_type:
                if company_id:
                    query += " AND"
                query += " event_type = ?"
                params.append(event_type.value)

        query += " ORDER BY timestamp DESC"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            events = []
            for row in cursor.fetchall():
                if row is None:
                    continue
                id, company_id, event_type_str, timestamp, details = row
                events.append(
                    Event(
                        id=id,
                        company_id=company_id or "",
                        event_type=EventType(event_type_str),
                        timestamp=dateutil.parser.parse(timestamp),
                        details=details,
                    )
                )
            return events


# Sample data
SAMPLE_COMPANIES = [
    Company(
        company_id="shopify",
        name="Shopify",
        details=CompaniesSheetRow(
            name="Shopify",
            type="Public",
            valuation="10B",
            url="https://shopify.com",
            updated=datetime.date(2024, 12, 15),
            eng_size=4000,
            total_size=10000,
            headquarters="Ottawa",
            remote_policy="Remote",
            email_thread_link="",
        ),
        recruiter_message=RecruiterMessage(
            message_id="1111",
            company_id="shopify",
            message="Hi Paul, are you interested in working as a staff developer at Shopify? Salary is $12k/year.  Regards, Bobby Bobberson",
            subject="Staff Developer Role at Shopify",
            sender="Bobby Bobberson",
            date=datetime.datetime(2024, 12, 15, 12, 0, 0, tzinfo=datetime.timezone.utc),
            email_thread_link="https://mail.google.com/mail/u/0/#label/jobs+2024%2Fshopify/QgrcJHrnzwvcPZNKHFvMjTVtJtGrWQflzqB",  # noqa: B950
            thread_id="QgrcJHrnzwvcPZNKHFvMjTVtJtGrWQflzqB",
        ),
    ),
    Company(
        company_id="rippling",
        name="Rippling",
        details=CompaniesSheetRow(
            name="Rippling",
            type="Private Unicorn",
            valuation="1500M",
            url="https://rippling.com",
            updated=datetime.date(2024, 10, 10),
            headquarters="New York",
            email_thread_link="https://mail.google.com/mail/u/0/#label/jobs+2024%2Frippling/QgrcJHrnzwvcPZNKHFvMjTVtJtGrWQflzqB",  # noqa: B950
        ),
        recruiter_message=RecruiterMessage(
            message_id="2222",
            company_id="rippling",
            message="Hi Paul! Interested in a senior backend role at Rippling working with AI? Work from anywhere. It pays $999,999. - Mark Marker",
            subject="Senior Backend Role at Rippling",
            sender="Mark Marker",
            date=datetime.datetime(2024, 10, 10, 12, 0, 0, tzinfo=datetime.timezone.utc),
            email_thread_link="https://mail.google.com/mail/u/0/#label/jobs+2024%2Frippling/QgrcJHrnzwvcPZNKHFvMjTVtJtGrWQflzqB",
            thread_id="QgrcJHrnzwvcPZNKHFvMjTVtJtGrWQflzqB",
        ),
    ),
]

# Module-level singleton
_company_repository = None


def company_repository(
    db_path: str = "data/companies.db",
    load_sample_data: bool = False,
    clear_data: bool = False,
) -> CompanyRepository:
    # This is a bit hacky: the args only matter when creating the singleton
    global _company_repository
    if _company_repository is None:
        _company_repository = CompanyRepository(
            db_path=db_path,
            load_sample_data=load_sample_data,
            clear_data=clear_data,
        )
    return _company_repository


def serialize_company(company: Company):
    data = company.model_dump()

    # Convert details to a simpler dict
    data["details"] = {
        k: (v.isoformat() if isinstance(v, datetime.date) else v)
        for k, v in company.details.model_dump().items()
        if v is not None
    }

    # Add promising directly at the top level for easier access from frontend
    data["promising"] = company.details.promising

    # Convert status to a simpler dict and include at top level for backward compatibility
    status_dict = company.status.model_dump()
    for key, value in status_dict.items():
        if isinstance(value, datetime.datetime):
            data[key] = value.isoformat()
        else:
            data[key] = value

    # Set sent_at based on reply_sent_at for backward compatibility
    if company.status.reply_sent_at:
        data["sent_at"] = company.status.reply_sent_at.isoformat()

    if company.recruiter_message:
        data["recruiter_message"] = company.recruiter_message.model_dump()
    else:
        data["recruiter_message"] = None

    # Include aliases if present
    aliases = getattr(company, "_aliases", None)
    if aliases is not None:
        data["aliases"] = aliases

    return data


def merge_company_data(
    existing_company: Company, sheet_row: CompaniesSheetRow
) -> Company:
    """Merge data from a spreadsheet row into an existing company.

    Rules for merging:
    1. Spreadsheet values take precedence if non-empty
    2. For date fields, use the most recent date
       a. For updated field, if neither exists, use today's date
    3. For notes field, append spreadsheet info instead of replacing

    Args:
        existing_company: The company from the database
        sheet_row: The company data from the spreadsheet

    Returns:
        The updated company with merged data
    """
    company = existing_company

    for field_name in sheet_row.__class__.model_fields.keys():
        sheet_value = getattr(sheet_row, field_name)

        if sheet_value in (None, "", []):
            continue

        # Special handling for date fields: use the most recent date
        if isinstance(sheet_value, datetime.date):
            db_value = getattr(company.details, field_name)
            if db_value and db_value > sheet_value:
                continue

        # Special handling for notes field - append instead of replace
        if field_name == "notes" and getattr(company.details, "notes"):
            existing_notes = getattr(company.details, "notes")
            if sheet_value and existing_notes:
                # Combine notes with a separator
                setattr(
                    company.details, field_name, f"{existing_notes}\n---\n{sheet_value}"
                )
                continue

        # For all other fields, spreadsheet value takes precedence
        setattr(company.details, field_name, sheet_value)

    if not company.details.updated:
        company.details.updated = datetime.date.today()

    return company


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    migration_group = parser.add_mutually_exclusive_group()
    migration_group.add_argument(
        "--migrate", action="store_true", help="Run database migrations"
    )
    migration_group.add_argument(
        "--migration-dir",
        default="migrations",
        help="Directory containing migration scripts (default: migrations)",
    )
    parser.add_argument("--clear-data", action="store_true", help="Clear existing data")
    parser.add_argument("--sample-data", action="store_true", help="Load sample data")
    parser.add_argument("--dump", action="store_true", help="Dump company data to stdout")
    parser.add_argument(
        "--dump-events", action="store_true", help="Dump events data to stdout"
    )
    parser.add_argument("--company", help="Filter events by company name")
    parser.add_argument(
        "--event-type", choices=[e.value for e in EventType], help="Filter events by type"
    )
    args = parser.parse_args()

    if args.migrate:
        import sys
        from pathlib import Path

        migration_dir = Path(args.migration_dir)
        if not migration_dir.exists():
            print(f"Migration directory {migration_dir} not found")
            sys.exit(1)

        migration_files = sorted(
            f for f in migration_dir.glob("*.py") if f.name != "__init__.py"
        )

        if not migration_files:
            print("No migration files found")
            sys.exit(0)

        print(f"Running {len(migration_files)} migrations from {migration_dir}")
        from importlib.util import module_from_spec, spec_from_file_location

        conn = sqlite3.connect("data/companies.db")
        try:
            for idx, path in enumerate(migration_files, 1):
                print(f"Running migration {idx}/{len(migration_files)}: {path.name}")
                try:
                    module_name = path.stem
                    assert module_name is not None

                    spec = spec_from_file_location(module_name, str(path))
                    assert spec is not None
                    module = module_from_spec(spec)
                    assert module is not None
                    assert spec.loader is not None
                    spec.loader.exec_module(module)
                    module.migrate(conn)
                    conn.commit()
                except Exception as e:
                    print(f"Failed to run migration {path.name}: {str(e)}")
                    conn.rollback()
                    sys.exit(1)
        finally:
            conn.close()
        sys.exit(0)

    repo = company_repository(
        clear_data=args.clear_data, load_sample_data=args.sample_data
    )

    if args.dump:
        for company in repo.get_all(include_messages=True):
            print(f"Company: {company.name}")
            print(company.model_dump_json(indent=2))
            if company.recruiter_message:
                print(company.recruiter_message.model_dump_json(indent=4))
            print()

    if args.dump_events:
        # Convert string event type to enum if provided
        event_type = None
        if args.event_type:
            event_type = EventType(args.event_type)

        events = repo.get_events(company_id=args.company, event_type=event_type)
        if not events:
            print("No events found matching the criteria")
        else:
            print(f"Found {len(events)} events:")
            for event in events:
                print(f"ID: {event.id}")
                print(f"Company: {event.company_id}")
                print(f"Type: {event.event_type.value}")
                print(f"Timestamp: {event.timestamp}")
                print("-" * 40)

                print(f"Timestamp: {event.timestamp}")
                print("-" * 40)

                print("-" * 40)
