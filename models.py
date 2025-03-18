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


class EventType(enum.Enum):
    REPLY_SENT = "reply_sent"
    RESEARCH_COMPLETED = "research_completed"
    COMPANY_CREATED = "company_created"
    COMPANY_UPDATED = "company_updated"
    RESEARCH_ERROR = "research_error"


class ResearchStepError(BaseModel):
    """Error information for a research step that failed."""

    step: str
    error: str
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class Event(BaseModel):
    """Event model for tracking company-related events"""

    id: Optional[int] = None
    company_name: str
    event_type: EventType
    timestamp: Optional[datetime.datetime] = None
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
                # (this prevents attribute errors when loading from eg old pickles that are missing fields)
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
        for field_name in self.model_fields.keys():
            value = getattr(self, field_name)
            yield str(value) if value is not None else ""

    def as_list_of_str(self) -> list[str]:
        """Convert row back to list of strings"""
        return list(self.iter_to_strs())

    def __len__(self) -> int:
        """Return the number of fields in the row"""
        return len(self.model_fields)

    def __str__(self) -> str:
        """Custom string representation showing only non-default values"""
        cls_name = self.__class__.__name__
        fields = []
        for name, field in self.model_fields.items():
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
            if 'List' in str(field.annotation) or 'list' in str(field.annotation):
                data[name] = field.default_factory() if hasattr(field, 'default_factory') else []
            else:
                data[name] = field.default
        
        # Update with values from row_data
        for name, value in zip(field_names, row_data):
            # Skip updating list fields with empty strings
            if value != "" or ('List' not in str(cls.model_fields[name].annotation) and 
                              'list' not in str(cls.model_fields[name].annotation)):
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
    updated: Optional[datetime.date] = Field(default=None)

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

    # Track research errors
    research_errors: List[ResearchStepError] = Field(default_factory=list)

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
        message: The content of the message
        subject: Email subject line
        sender: Email sender (recruiter's email address)
        email_thread_link: URL to the email thread in Gmail
        thread_id: Gmail thread ID
        date: Timestamp of the message as UTC datetime
    """

    message_id: str = ""
    message: str = ""
    subject: Optional[str] = ""
    sender: Optional[str] = ""
    email_thread_link: str = ""
    thread_id: str = ""
    date: Optional[datetime.datetime] = None


class Company(BaseModel):
    name: str
    updated_at: Optional[datetime.datetime] = None
    details: CompaniesSheetRow
    reply_message: str = ""
    message_id: Optional[str] = None
    recruiter_message: Optional[RecruiterMessage] = None

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
            self.recruiter_message = RecruiterMessage(message=message)
        else:
            self.recruiter_message.message = message


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        if isinstance(obj, enum.Enum):
            return obj.value
        if isinstance(obj, Event):
            return {
                "id": obj.id,
                "company_name": obj.company_name,
                "event_type": obj.event_type.value,
                "timestamp": obj.timestamp.isoformat() if obj.timestamp else None,
                "details": obj.details,
            }
        if isinstance(obj, ResearchStepError):
            return {
                "step": obj.step,
                "error": obj.error,
                "timestamp": obj.timestamp.isoformat() if obj.timestamp else None,
            }
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
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

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
                        name TEXT PRIMARY KEY,
                        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                        details TEXT NOT NULL,
                        reply_message TEXT,
                        message_id TEXT
                    )
                """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS recruiter_messages (
                        message_id TEXT PRIMARY KEY,
                        subject TEXT DEFAULT '',
                        sender TEXT DEFAULT '',
                        message TEXT DEFAULT '',
                        thread_id TEXT NOT NULL,
                        email_thread_link TEXT DEFAULT '',
                        date TEXT DEFAULT ''
                    )
                """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                        details TEXT,
                        FOREIGN KEY (company_name) REFERENCES companies (name)
                    )
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

    def get(self, name: str) -> Optional[Company]:
        # Reads can happen without the lock
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name, updated_at, details, reply_message, message_id FROM companies WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            company = self._deserialize_company(row) if row else None
            if company and company.message_id:
                message = self._get_recruiter_message(company.message_id, conn)
                company.recruiter_message = message
        return company

    def get_recruiter_message(self, message_id: str) -> Optional[RecruiterMessage]:
        """
        Get a single recruiter message by its message_id.
        """
        with self._get_connection() as conn:
            return self._get_recruiter_message(message_id, conn)

    def _get_recruiter_message(
        self, message_id: str, conn: sqlite3.Connection
    ) -> Optional[RecruiterMessage]:
        cursor = conn.execute(
            "SELECT message_id, subject, sender, message, thread_id, email_thread_link, date FROM recruiter_messages WHERE message_id = ?",
            (message_id,),
        )
        row = cursor.fetchone()
        if row:
            # Parse the date string to datetime if it exists
            date_str = row[6]
            date = None
            if date_str:
                try:
                    date = dateutil.parser.parse(date_str).replace(
                        tzinfo=datetime.timezone.utc
                    )
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse date string: {date_str}")

            recruiter_message = RecruiterMessage(
                message_id=row[0],
                subject=row[1],
                sender=row[2],
                message=row[3],
                thread_id=row[4],
                email_thread_link=row[5],
                date=date,
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

        try:
            # Try to insert first
            conn.execute(
                """
                INSERT INTO recruiter_messages (
                    message_id, subject, sender, message, thread_id, email_thread_link, date
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.subject,
                    message.sender,
                    message.message,
                    message.thread_id,
                    message.email_thread_link,
                    date_str,
                ),
            )
        except sqlite3.IntegrityError:
            # If it already exists, update it
            conn.execute(
                """
                UPDATE recruiter_messages
                SET subject = ?, sender = ?, message = ?, thread_id = ?, email_thread_link = ?, date = ?
                WHERE message_id = ?
                """,
                (
                    message.subject,
                    message.sender,
                    message.message,
                    message.thread_id,
                    message.email_thread_link,
                    date_str,
                    message.message_id,
                ),
            )

    def get_all(self, include_messages=False) -> List[Company]:
        # Reads can happen without the lock
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name, updated_at, details, reply_message, message_id FROM companies"
            )
            companies = [self._deserialize_company(row) for row in cursor.fetchall()]
            if include_messages:
                # Don't worry about this being slow for now
                for comp in companies:
                    if comp.message_id:
                        message = self._get_recruiter_message(comp.message_id, conn)
                        comp.recruiter_message = message
            return companies

    def create(self, company: Company) -> Company:
        with self.lock:
            with self._get_connection() as conn:
                try:
                    # Store message_id from recruiter_message if available
                    message_id = None
                    if company.recruiter_message and company.recruiter_message.message_id:
                        message_id = company.recruiter_message.message_id
                    elif company.message_id:
                        message_id = company.message_id

                    conn.execute(
                        """
                        INSERT INTO companies (
                            name, details, reply_message, message_id
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            company.name,
                            json.dumps(
                                company.details.model_dump(), cls=CustomJSONEncoder
                            ),
                            company.reply_message,
                            message_id,
                        ),
                    )

                    # Save the recruiter message if it exists
                    if company.recruiter_message and company.recruiter_message.message_id:
                        self._upsert_recruiter_message(company.recruiter_message, conn)

                    conn.commit()
                    refreshed_company = self.get(
                        company.name
                    )  # To include generated timestamp
                    assert refreshed_company is not None
                    return refreshed_company
                except sqlite3.IntegrityError:
                    raise ValueError(f"Company {company.name} already exists")

    def update(self, company: Company) -> Company:
        with self.lock:  # Lock for writes
            with self._get_connection() as conn:
                # Get message_id from recruiter_message if available
                message_id = None
                if company.recruiter_message and company.recruiter_message.message_id:
                    message_id = company.recruiter_message.message_id
                elif company.message_id:
                    message_id = company.message_id

                cursor = conn.execute(
                    """
                    UPDATE companies 
                    SET details = ?, 
                        reply_message = ?,
                        message_id = ?,
                        updated_at = datetime('now')
                    WHERE name = ?
                    """,
                    (
                        json.dumps(company.details.model_dump(), cls=CustomJSONEncoder),
                        company.reply_message,
                        message_id,
                        company.name,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ValueError(f"Company {company.name} not found")

                # Update or create the recruiter message if it exists
                if company.recruiter_message and company.recruiter_message.message_id:
                    # Use the upsert method to handle both new and existing messages
                    self._upsert_recruiter_message(company.recruiter_message, conn)

                conn.commit()
                refreshed_company = self.get(
                    company.name
                )  # To include generated timestamp
                assert refreshed_company is not None
                return refreshed_company

    def delete(self, name: str) -> None:
        with self.lock:  # Lock for writes
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM companies WHERE name = ?", (name,))
                if cursor.rowcount == 0:
                    raise ValueError(f"Company {name} not found")
                conn.commit()

    def _deserialize_company(self, row: tuple) -> Company:
        """Convert a database row into a Company object."""
        assert row is not None
        name, updated_at, details_json, reply_message, message_id = row
        details_dict = json.loads(details_json)

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

        return Company(
            name=name,
            updated_at=updated_at_dt,
            details=CompaniesSheetRow(**details_dict),
            reply_message=reply_message,
            message_id=message_id,
        )

    def create_event(self, event: Event) -> Event:
        """Create a new event record"""
        if not event.timestamp:
            event.timestamp = datetime.datetime.now(datetime.timezone.utc)

        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO events (company_name, event_type, timestamp, details)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        event.company_name,
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
        self, company_name: Optional[str] = None, event_type: Optional[EventType] = None
    ) -> List[Event]:
        """Get events, optionally filtered by company name and/or event type"""
        query = "SELECT id, company_name, event_type, timestamp, details FROM events"
        params = []

        if company_name or event_type:
            query += " WHERE"

            if company_name:
                query += " company_name = ?"
                params.append(company_name)

            if event_type:
                if company_name:
                    query += " AND"
                query += " event_type = ?"
                params.append(event_type.value)

        query += " ORDER BY timestamp DESC"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            events = []
            for row in cursor.fetchall():
                id, company_name, event_type_str, timestamp, details = row
                events.append(
                    Event(
                        id=id,
                        company_name=company_name or "",
                        event_type=EventType(event_type_str),
                        timestamp=dateutil.parser.parse(timestamp),
                        details=details,
                    )
                )
            return events


# Sample data
SAMPLE_COMPANIES = [
    Company(
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
        message_id="1111",
        recruiter_message=RecruiterMessage(
            message_id="1111",
            message="Hi Paul, are you interested in working as a staff developer at Shopify? Salary is $12k/year.  Regards, Bobby Bobberson",
            subject="Staff Developer Role at Shopify",
            sender="Bobby Bobberson",
            date=datetime.datetime(2024, 12, 15, 12, 0, 0, tzinfo=datetime.timezone.utc),
            email_thread_link="https://mail.google.com/mail/u/0/#label/jobs+2024%2Fshopify/QgrcJHrnzwvcPZNKHFvMjTVtJtGrWQflzqB",
            thread_id="QgrcJHrnzwvcPZNKHFvMjTVtJtGrWQflzqB",
        ),
    ),
    Company(
        name="Rippling",
        details=CompaniesSheetRow(
            name="Rippling",
            type="Private Unicorn",
            valuation="1500M",
            url="https://rippling.com",
            updated=datetime.date(2024, 10, 10),
            headquarters="New York",
            email_thread_link="https://mail.google.com/mail/u/0/#label/jobs+2024%2Frippling/QgrcJHrnzwvcPZNKHFvMjTVtJtGrWQflzqB",
        ),
        message_id="2222",
        recruiter_message=RecruiterMessage(
            message_id="2222",
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
    data["details"] = {
        k: (v.isoformat() if isinstance(v, datetime.date) else v)
        for k, v in company.details.model_dump().items()
        if v is not None
    }
    if company.recruiter_message:
        data["recruiter_message"] = company.recruiter_message.model_dump()
    else:
        data["recruiter_message"] = None
    return data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
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

        events = repo.get_events(company_name=args.company, event_type=event_type)
        if not events:
            print("No events found matching the criteria")
        else:
            print(f"Found {len(events)} events:")
            for event in events:
                print(f"ID: {event.id}")
                print(f"Company: {event.company_name}")
                print(f"Type: {event.event_type.value}")
                print(f"Timestamp: {event.timestamp}")
                print("-" * 40)
