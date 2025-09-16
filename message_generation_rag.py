import logging
import os
from typing import List, Tuple

from langchain_anthropic import ChatAnthropic
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ai.client_factory import get_chat_client
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
        # Only add the documents to the vectorstore if it's empty
        has_data = bool(vectorstore.get(limit=1, include=[])["ids"])
        if has_data and not clear_existing:
            logger.info(f"Loaded vector store for {collection_name}")
            return vectorstore

        if clear_existing:
            vectorstore.reset_collection()

        documents = []
        for subject, recruiter_message, my_reply in self.messages:
            text = f"Subject: {subject}\nRecruiter: {recruiter_message}\nMy Reply: {my_reply}"
            documents.append(Document(page_content=text))

        logger.info("Adding initial documents to the vector store from split data")

        split_docs = self.text_splitter.split_documents(documents)
        vectorstore.add_documents(split_docs)
        return vectorstore

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

        if provider:
            llm: BaseChatModel = get_chat_client(
                provider=provider,
                model=llm_type,
                temperature=TEMPERATURE,
                timeout=TIMEOUT,
            )
        else:
            if llm_type.lower() == "openai":
                llm: BaseChatModel = ChatOpenAI(temperature=TEMPERATURE, timeout=TIMEOUT)
            elif llm_type.lower() == "claude":
                llm = ChatAnthropic(
                    model="claude-3-5-sonnet-20240620",  # type: ignore[call-arg]
                    temperature=TEMPERATURE,
                    timeout=TIMEOUT,
                )
            elif llm_type.startswith("gpt"):
                llm = ChatOpenAI(model=llm_type, temperature=TEMPERATURE)
            elif llm_type.startswith("claude"):
                llm = ChatAnthropic(
                    model=llm_type,  # type: ignore[call-arg]
                    temperature=TEMPERATURE,
                    timeout=TIMEOUT,
                )
            else:
                raise ValueError(
                    "Invalid llm_type. Choose 'openai' or 'claude' or 'gpt'."
                )

        prompt = ChatPromptTemplate.from_template(TEMPLATE)

        self.chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

    def generate_reply(self, new_recruiter_message: str) -> str:
        if self.chain is None:
            raise ValueError("Chain not set up. Call setup_chain() first.")
        return self.chain.invoke(new_recruiter_message)
