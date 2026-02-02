import logging
import os
import re
import shutil
from typing import List, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ai.client_factory import get_chat_client

logger = logging.getLogger(__name__)

TEMPLATE = """You are an AI assistant helping to generate replies to recruiter messages
based on previous interactions.
Use the following pieces of context to generate a reply to the recruiter message.
The reply should be professional, courteous, and in a similar style and length
to the previous context.
Also observe these additional constraints on style:
- Be concise.
- Do not use bullet points.
- Avoid redundancy.
- Do not be apologetic.
- Do not exceed 100 words.
- Don't use superlatives.
Also observe these additional constraints on generated content:
- Assume that this is my first reply to this particular recruiter.
- If the recruiter message provides specific information that is an especially good match for
  most or all the criteria that previous context has indicated the candidate wants,
  then the tone should be more excited.
- Never decline opportunities with compensation that is higher than the desired range!
  Higher is better, and no amount is too high!
- If declining because of low compensation, always include specific desired
  total compensation based on the Shopify example.
- If declining because of other criteria, be specific about the criteria that are not met.
- If mentioning my previous roles by title, only mention the staff developer role.
- If they require full stack or javascript, mention that those aren't my strengths.
- Desired locations are NYC (New York City), or remote. No relocations.

Context: {context}

Recruiter Message: {question}

Generated Reply:"""


HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")


class RecruitmentRAG:

    def __init__(self, messages: List[Tuple[str, str, str]], loglevel=logging.INFO):
        if len(messages) == 0:
            raise ValueError("No messages provided")
        self.messages = messages
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        self.vectorstore = None
        self.retriever = None
        self.chain = None
        logger.setLevel(loglevel)

    def make_replies_vector_db(self, clear_existing: bool = False):
        collection_name = "recruiter-replies"
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=DATA_DIR,
        )
        if clear_existing:
            # When the persisted Chroma store is corrupted or out of sync (issue #108),
            # treat it as recoverable and rebuild from source messages.
            try:
                vectorstore.reset_collection()
            except Exception:
                logger.warning(
                    "Failed to reset Chroma collection; attempting to repair persisted store",
                    exc_info=True,
                )
                self._repair_chroma_persisted_store()
                vectorstore = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=DATA_DIR,
                )
                vectorstore.reset_collection()
        else:
            # Only add the documents to the vectorstore if it's empty.
            # Chroma can raise errors like:
            #   "Error getting collection: Collection [<uuid>] does not exists."
            # Treat this as a recoverable condition and rebuild from scratch.
            try:
                has_data = bool(vectorstore.get(limit=1, include=[])["ids"])
            except Exception:
                logger.warning(
                    "Error reading Chroma collection; rebuilding vector store",
                    exc_info=True,
                )
                return self.make_replies_vector_db(clear_existing=True)

            if has_data:
                logger.info(f"Loaded vector store for {collection_name}")
                return vectorstore

        documents = []
        for subject, recruiter_message, my_reply in self.messages:
            text = f"Subject: {subject}\nRecruiter: {recruiter_message}\nMy Reply: {my_reply}"
            documents.append(Document(page_content=text))

        logger.info("Adding initial documents to the vector store from split data")

        split_docs = self.text_splitter.split_documents(documents)
        vectorstore.add_documents(split_docs)
        return vectorstore

    def _repair_chroma_persisted_store(self) -> None:
        """
        Best-effort repair of Chroma persistence when the collection metadata is out of sync.

        This only removes Chroma-specific artifacts inside DATA_DIR, leaving unrelated DBs
        (like companies/tasks) intact.
        """
        if not os.path.isdir(DATA_DIR):
            return

        # Chroma uses a sqlite db plus UUID-ish segment directories for indexes.
        uuid_dir_re = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )

        for name in os.listdir(DATA_DIR):
            path = os.path.join(DATA_DIR, name)
            if os.path.isfile(path) and name.startswith("chroma.sqlite3"):
                try:
                    os.remove(path)
                except OSError:
                    logger.warning(f"Failed to remove {path}", exc_info=True)
                continue

            if os.path.isdir(path) and uuid_dir_re.match(name):
                # Only delete if it looks like a Chroma index directory.
                try:
                    entries = set(os.listdir(path))
                except OSError:
                    logger.warning(f"Failed to list {path}", exc_info=True)
                    continue

                if {
                    "data_level0.bin",
                    "header.bin",
                    "length.bin",
                    "link_lists.bin",
                } <= entries:
                    try:
                        shutil.rmtree(path)
                    except OSError:
                        logger.warning(
                            f"Failed to remove directory {path}", exc_info=True
                        )

    def prepare_data(self, clear_existing: bool = False):
        self.vectorstore = self.make_replies_vector_db(clear_existing=clear_existing)
        if self.vectorstore is None:
            raise ValueError("Failed to create vectorstore")
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})

    def setup_chain(self, llm_type: str, provider: str | None = None):
        if self.retriever is None:
            raise ValueError("Data not prepared. Call prepare_data() first.")

        TEMPERATURE = 0.2  # Lowish because we're writing email to real people.
        TIMEOUT = 120

        # Infer provider/model if not explicitly provided
        model_to_use = llm_type
        resolved_provider = provider
        if resolved_provider is None:
            lt = llm_type.lower()
            if lt == "openai":
                resolved_provider = "openai"
                model_to_use = "gpt-4o"
            elif lt == "claude":
                resolved_provider = "anthropic"
                model_to_use = "claude-3-5-sonnet-20240620"
            elif lt.startswith("gpt"):
                resolved_provider = "openai"
            elif lt.startswith("claude"):
                resolved_provider = "anthropic"
            else:
                raise ValueError(
                    "Invalid llm_type. Choose 'openai' or 'claude' or a specific model starting with 'gpt' or 'claude'."
                )

        llm_client = get_chat_client(
            provider=resolved_provider,
            model=model_to_use,
            temperature=TEMPERATURE,
            timeout=TIMEOUT,
        )
        # Normalize to callable so both real clients (runnable) and test doubles with .invoke work
        if callable(llm_client):
            llm = llm_client
        else:

            def _llm_invoke(input, _llm=llm_client):
                return _llm.invoke(input)

            llm = _llm_invoke

        prompt = ChatPromptTemplate.from_template(TEMPLATE)

        # Ensure the retriever is runnable-like for LangChain.
        # LangChain accepts a callable, Runnable or dict. Tests inject a simple
        # object with an `invoke` method, so wrap it in a callable if needed.
        if callable(self.retriever):
            context_runnable = self.retriever
        else:

            def _context_callable(input, retr=self.retriever):
                return retr.invoke(input)

            context_runnable = _context_callable

        self.chain = (
            {"context": context_runnable, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

    def generate_reply(self, new_recruiter_message: str) -> str:
        if self.chain is None:
            raise ValueError("Chain not set up. Call setup_chain() first.")
        return self.chain.invoke(new_recruiter_message)
