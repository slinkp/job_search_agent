from unittest import mock

from langchain_core.documents import Document

from message_generation_rag import RecruitmentRAG


def test_rag_repairs_missing_chroma_collection_by_rebuilding():
    """
    Repro for issue #108:
    Chroma may raise "Collection [<uuid>] does not exists" when reading persisted state.
    The RAG should treat this as recoverable and rebuild the collection.
    """

    messages = [("subj", "recruiter body", "my reply")]
    rag = RecruitmentRAG(messages)

    # Avoid relying on actual splitting behavior in this unit test.
    rag.text_splitter = mock.Mock()
    rag.text_splitter.split_documents.return_value = [Document(page_content="x")]

    broken_vs = mock.Mock()
    broken_vs.get.side_effect = RuntimeError(
        "Error getting collection: Collection [2eaeed3e-3772-437d-9ff7-d8ec51dc670e] does not exists."
    )

    rebuilt_vs = mock.Mock()

    with mock.patch("message_generation_rag.Chroma", autospec=True) as chroma_cls:
        chroma_cls.side_effect = [broken_vs, rebuilt_vs]
        out = rag.make_replies_vector_db(clear_existing=False)

    assert out is rebuilt_vs
    rebuilt_vs.reset_collection.assert_called_once_with()
    rebuilt_vs.add_documents.assert_called_once()
