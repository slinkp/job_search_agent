import base64
import logging
import os
import re
import textwrap
from collections import defaultdict

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

HERE = os.path.dirname(os.path.abspath(__file__))
AUTH_DIR = os.path.join(HERE, "secrets")
CREDENTIALS_FILE = os.path.join(AUTH_DIR, "credentials.json")
TOKEN_FILE = os.path.join(AUTH_DIR, "token.json")


ARCHIVED_LABEL = "jobs-2024/recruiter-pings-archived"
RECRUITER_REPLIES_QUERY = f"label:{ARCHIVED_LABEL} from:me"
RECRUITER_MESSSAGES_LABEL = "jobs-2024/recruiter-pings"
RECRUITER_MESSAGES_QUERY = f"label:{RECRUITER_MESSSAGES_LABEL}"
RECRUITER_MESSAGES_LINK_TEMPLATE = (
    "https://mail.google.com/mail/u/0/#label/jobs+2024%2Frecruiter+pings/{thread_id}"
)

logger = logging.getLogger(__name__)

class GmailRepliesSearcher:
    """
    Searches for user's previous replies to recruiter emails.

    Intended to be used to feed into a RAG system to help it understand the
    user's communication style.
    """

    SCOPES = (
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.modify",
    )

    def __init__(self):
        self.creds = None
        self._service = None

    @property
    def service(self) -> Resource:
        if self._service is None:
            self.authenticate()
        assert self._service is not None
        return self._service

    def authenticate(self):
        if os.path.exists(TOKEN_FILE):
            self.creds = Credentials.from_authorized_user_file(TOKEN_FILE, self.SCOPES)
        if not (self.creds and self.creds.valid):
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except RefreshError:
                    # Token is invalid, so we need to re-authenticate
                    self.creds = None
            if not self.creds or not self.creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as token:
                token.write(self.creds.to_json())
        self._service = build("gmail", "v1", credentials=self.creds)

    def search_messages(self, query, max_results: int = 10) -> list:
        messages_resource = self.service.users().messages()  # type: ignore
        results: dict = messages_resource.list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = results.get("messages", [])
        return messages

    def get_message_details(self, msg_id) -> dict:
        messages_resource = self.service.users().messages()  # type: ignore
        message: dict = messages_resource.get(userId="me", id=msg_id).execute()
        return message

    def search_and_get_details(self, query, max_results: int = 10):
        messages = self.search_messages(query, max_results)
        detailed_messages = [self.get_message_details(msg["id"]) for msg in messages]
        return detailed_messages

    def extract_message_content(self, message):
        try:
            # Attempt to access the 'data' key
            data = message["payload"]["body"]["data"]
            return base64.urlsafe_b64decode(data).decode()
        except KeyError:
            # If 'data' is not found, check for 'parts'
            parts = message["payload"].get("parts", [])
            if parts:
                for part in parts:
                    if part["mimeType"] == "text/plain":
                        data = part["body"]["data"]
                        return base64.urlsafe_b64decode(data).decode()

        logger.error("No content found in message")
        return ""

    def clean_reply(self, text):
        text = text.strip()
        if len(text) < 30:
            # Heuristic for stuff like 'replied on linkedin'
            return ""
        return text

    def _is_garbage_line(self, line):
        linkedin_garbage_lines_starters = (
            "This email was intended for",
            "Get the new LinkedIn",
            "Also available on mobile",
            "*Tip:* You can respond to ",
            "See all connections in common",
            "View profile:",
            "Accept:http",
            "You have an invitation",
            "-------------------------------",
        )
        for garbage in linkedin_garbage_lines_starters:
            if line.startswith(garbage):
                return True
        linkedin_garbage_lines_exact = [
            "Reply",
            "You have an invitation",
        ]
        for garbage in linkedin_garbage_lines_exact:
            if line == garbage:
                return True
        return False

    def clean_quoted_text(self, text):
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            line = line.lstrip("> ")
            line = re.sub(r"<\S+>", "", line)
            line = re.sub(r"\[image:.*?\]", "", line, flags=re.MULTILINE)
            line = line.strip()
            if self._is_garbage_line(line):
                break
            if line:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def split_message(self, content):
        pattern = r"\nOn .+?(?:\d{1,2}:\d{2}(?: [AP]M)?|\d{4}).*?(?:\S+@\S+|<\S+@\S+>)\s+wrote:"
        match = re.split(pattern, content, flags=re.DOTALL | re.IGNORECASE)
        if len(match) > 1:
            reply_text = self.clean_reply(match[0])
            quoted_text = self.clean_quoted_text(match[-1])
        else:
            reply_text = self.clean_reply(content)
            quoted_text = ""
        return reply_text, quoted_text

    def get_subject(self, message) -> str:
        garbage_subjects = [
            "You have an invitation",
        ]
        for header in message["payload"]["headers"]:
            if header["name"].lower() == "subject":
                subject = header["value"].strip()
                if subject and subject not in garbage_subjects:
                    return subject
        return "(No Subject)"

    def get_my_replies_to_recruiters(
        self, query: str = RECRUITER_REPLIES_QUERY, max_results: int = 10
    ) -> list[tuple[str, str, str]]:
        results = self.search_and_get_details(query, max_results)
        print(f"Got {len(results)} messages")
        processed_messages = []

        for full_msg in results:
            subject = self.get_subject(full_msg)
            content = self.extract_message_content(full_msg)
            date = full_msg["internalDate"]
            my_reply, recruiter_message = self.split_message(content)
            if my_reply and recruiter_message:
                processed_messages.append(
                    (date, (subject, recruiter_message, my_reply))
                )
            else:
                print(f"Skipping message with no useful content: {subject}")

        processed_messages.sort(reverse=True)
        return [msg for _, msg in processed_messages]

    def get_new_recruiter_messages(self, max_results: int = 10) -> list[dict]:
        """
        Get new messages from recruiters that we haven't replied to yet.
        Combines messages in each thread and returns a list of dicts.

        Includes latest subject.
        """
        logger.info(f"Getting {max_results} new recruiter messages...")
        message_dicts = self.search_and_get_details(
            RECRUITER_MESSAGES_QUERY, max_results
        )
        logger.info(f"...Got {len(message_dicts)} raw recruiter messages")
        content_by_thread = defaultdict(list)
        for msg_dict in message_dicts:
            thread_id = msg_dict["threadId"]
            content = self.extract_message_content(msg_dict)
            content = self.clean_quoted_text(content)
            date = msg_dict["internalDate"]
            content_by_thread[thread_id].append((date, content, msg_dict))

        combined_messages = []
        for thread_id, msg_list in content_by_thread.items():
            # Sort a thread by date, oldest first.
            msg_list.sort(key=lambda x: x[0])
            combined_msg = msg_list[-1][-1].copy()  # Use the latest dict
            # Concatenate the text content of all messages in the thread.
            # And the oldest message's subject.
            # TODO: Linkedin subjects may be redundant copy of message content,
            # but that's probably ok
            subject = self.get_subject(msg_list[0][-1]).strip()

            email_thread_link = self._get_email_thread_link(msg_list)
            combined_msg["email_thread_link"] = email_thread_link
            combined_content = []
            if subject:
                subject = subject.strip() + "\n\n"
                combined_content.append(subject)

            combined_content.extend(
                [self.extract_message_content(mdict[2]) for mdict in msg_list]
            )

            if len(combined_content) > 1:
                # We drop the subject if it's redundant.
                if combined_content[1].startswith(combined_content[0].rstrip()):
                    combined_content = combined_content[1:]

            for i, content in enumerate(combined_content):
                logger.debug(f"Thread {thread_id} content {i}:\n{content[:200]}...")

            # TODO: Add text extracted from attached PDFs, docx, etc.
            combined_msg["combined_content"] = "\n\n".join(combined_content)
            combined_messages.append(combined_msg)

        combined_messages.sort(key=lambda x: int(x["internalDate"]), reverse=True)
        logger.info(
            f"Got {len(message_dicts)} new recruiter messages in {len(combined_messages)} threads"
        )
        return combined_messages

    def _get_email_thread_link(self, msg_list) -> str:
        thread_id = msg_list[-1][-1]["threadId"]
        email_thread_link = RECRUITER_MESSAGES_LINK_TEMPLATE.format(thread_id=thread_id)
        return email_thread_link
        
    def send_reply(self, thread_id: str, message_id: str, reply_text: str) -> bool:
        """
        Send a reply to a specific message in a thread.
        
        Args:
            thread_id: The Gmail thread ID
            message_id: The specific message ID to reply to
            reply_text: The content of the reply
            
        Returns:
            bool: True if successful, False otherwise
        """
        import base64
        from email.mime.text import MIMEText
        
        try:
            # Get the original message to extract headers
            original_message = self.service.users().messages().get(
                userId='me', id=message_id
            ).execute()
            
            # Extract headers from original message
            headers = {}
            for header in original_message['payload']['headers']:
                headers[header['name']] = header['value']
            
            # Create reply subject (Re: original subject)
            original_subject = headers.get('Subject', '')
            if original_subject.startswith('Re:'):
                subject = original_subject
            else:
                subject = f"Re: {original_subject}"
            
            # Create message
            message = MIMEText(reply_text)
            message['To'] = headers.get('From', '')
            message['Subject'] = subject
            message['In-Reply-To'] = headers.get('Message-ID', '')
            message['References'] = headers.get('Message-ID', '')
            
            # Encode the message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            # Send the message
            sent_message = self.service.users().messages().send(
                userId='me',
                body={
                    'raw': raw_message,
                    'threadId': thread_id
                }
            ).execute()
            
            logger.info(f"Reply sent successfully. Message ID: {sent_message['id']}")
            return True
            
        except Exception as error:
            logger.error(f"Error sending reply: {error}")
            return False
            
    def archive_message(self, message_id: str) -> bool:
        """
        Archive a message by removing the INBOX label.
        
        Args:
            message_id: The message ID to archive
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'removeLabelIds': ['INBOX']
                }
            ).execute()
            
            logger.info(f"Message {message_id} archived successfully")
            return True
            
        except Exception as error:
            logger.error(f"Error archiving message: {error}")
            return False
    
    def add_label(self, message_id: str, label_name: str) -> bool:
        """
        Add a label to a message.
        Creates the label if it doesn't exist.
        
        Args:
            message_id: The message ID
            label_name: The name of the label to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all labels
            labels = self.service.users().labels().list(userId='me').execute()
            label_id = None
            
            # Check if label exists
            for label in labels.get('labels', []):
                if label['name'] == label_name:
                    label_id = label['id']
                    break
            
            # Create label if it doesn't exist
            if not label_id:
                created_label = self.service.users().labels().create(
                    userId='me',
                    body={
                        'name': label_name,
                        'labelListVisibility': 'labelShow',
                        'messageListVisibility': 'show'
                    }
                ).execute()
                label_id = created_label['id']
                logger.info(f"Created new label: {label_name}")
            
            # Add label to message
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': [label_id]
                }
            ).execute()
            
            logger.info(f"Added label {label_name} to message {message_id}")
            return True
            
        except Exception as error:
            logger.error(f"Error adding label: {error}")
            return False


def main_demo(
    do_replies: bool, do_recruiter_messages: bool, max_lines: int, max_results: int
):
    searcher = GmailRepliesSearcher()
    query = RECRUITER_REPLIES_QUERY

    term_width = 75

    processed_messages = []
    recruiter_messages = []
    if do_replies:
        processed_messages = searcher.get_my_replies_to_recruiters(
            query, max_results=max_results + 10
        )
        processed_messages = processed_messages[:max_results]

    if do_recruiter_messages:
        recruiter_messages = searcher.get_new_recruiter_messages(
            max_results=max_results
        )

    for i, msg in enumerate(recruiter_messages):
        print(f"Recruiter Message {i}:")
        print()
        msg = textwrap.fill(
            msg["combined_content"], width=term_width, max_lines=max_lines
        )
        print(msg)
        print()
        print("-" * term_width)
        print()

    for i, (subject, recruiter_message, my_reply) in enumerate(processed_messages):
        subject = textwrap.fill(subject, width=term_width)
        recruiter_message = textwrap.fill(
            recruiter_message, width=term_width, max_lines=max_lines
        )
        my_reply = textwrap.fill(my_reply, width=term_width, max_lines=max_lines)
        print(f"Message {i} Subject: {subject}")
        print(f"\nRecruiter Message:\n{recruiter_message}")
        print(f"\nMy Reply:\n{my_reply}")
        print()
        print("-" * term_width)
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--replies", action="store_true")
    parser.add_argument("--recruiter-messages", action="store_true")
    parser.add_argument("--max-lines", type=int, default=10)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if not args.replies and not args.recruiter_messages:
        print("Please specify at least one of --replies or --recruiter-messages")
        exit(1)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    main_demo(
        do_replies=args.replies,
        do_recruiter_messages=args.recruiter_messages,
        max_lines=args.max_lines,
        max_results=args.max_results,
    )
