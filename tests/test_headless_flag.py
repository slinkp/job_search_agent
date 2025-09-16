import libjobsearch


class DummyEmailResponseGenerator:
    def __init__(
        self, reply_rag_model, reply_rag_limit, loglevel, cache_settings, provider=None
    ):
        pass

    def get_new_recruiter_messages(self, max_results=100):
        return []

    def generate_reply(self, msg: str) -> str:
        return "ok"


def test_jobsearch_headless_defaults_true(monkeypatch):
    parser = libjobsearch.arg_parser()
    args = parser.parse_args([])  # no --no-headless
    monkeypatch.setattr(
        libjobsearch, "EmailResponseGenerator", DummyEmailResponseGenerator
    )
    js = libjobsearch.JobSearch(
        args, loglevel=0, cache_settings=libjobsearch.CacheSettings()
    )
    assert js.headless is True


def test_jobsearch_no_headless_sets_visible(monkeypatch):
    parser = libjobsearch.arg_parser()
    args = parser.parse_args(["--no-headless"])
    monkeypatch.setattr(
        libjobsearch, "EmailResponseGenerator", DummyEmailResponseGenerator
    )
    js = libjobsearch.JobSearch(
        args, loglevel=0, cache_settings=libjobsearch.CacheSettings()
    )
    assert js.headless is False
