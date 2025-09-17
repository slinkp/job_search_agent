import argparse

from libjobsearch import arg_parser, select_provider_and_model, SONNET_LATEST


def test_defaults_no_flags():
    parser = arg_parser()
    args = parser.parse_args([])
    provider, model = select_provider_and_model(args)
    assert provider == "anthropic"
    assert model == SONNET_LATEST


def test_openrouter_defaults_model():
    parser = arg_parser()
    args = parser.parse_args(["--provider", "openrouter"])
    provider, model = select_provider_and_model(args)
    assert provider == "openrouter"
    assert model == "gpt-5-mini"


def test_model_implies_provider_openai():
    parser = arg_parser()
    args = parser.parse_args(["--model", "gpt-4o"])
    provider, model = select_provider_and_model(args)
    assert provider == "openai"
    assert model == "gpt-4o"


def test_model_implies_provider_anthropic():
    parser = arg_parser()
    args = parser.parse_args(["--model", SONNET_LATEST])
    provider, model = select_provider_and_model(args)
    assert provider == "anthropic"
    assert model == SONNET_LATEST


def test_both_given_preserved():
    parser = arg_parser()
    args = parser.parse_args(["--provider", "openrouter", "--model", "gpt-5"])
    provider, model = select_provider_and_model(args)
    assert provider == "openrouter"
    assert model == "gpt-5"
