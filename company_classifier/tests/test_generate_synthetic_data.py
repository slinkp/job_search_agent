"""
Unit tests for generate_synthetic_data.py argument parsing functionality.
"""

import argparse
from unittest.mock import patch

import pytest

from company_classifier.generate_synthetic_data import parse_args


class TestParseArgs:
    """Test argument parsing for synthetic data generation."""

    def test_default_args(self):
        """Test that default arguments are set correctly when no args are provided."""
        with patch(
            "argparse.ArgumentParser.parse_args",
            return_value=argparse.Namespace(
                num_companies=1000,
                output_dir="data/synthetic",
                stdout=False,
                generator="random",
                model="gpt-4-turbo-preview",
                train_ratio=0.7,
                val_ratio=0.15,
                test_ratio=0.15,
                random_seed=42,
            ),
        ):
            args = parse_args()

            # Check default values
            assert args.num_companies == 1000
            assert args.output_dir == "data/synthetic"
            assert args.stdout is False
            assert args.generator == "random"
            assert args.model == "gpt-4-turbo-preview"
            assert args.train_ratio == 0.7
            assert args.val_ratio == 0.15
            assert args.test_ratio == 0.15
            assert args.random_seed == 42

    def test_custom_args(self):
        """Test that custom arguments override defaults."""
        test_args = [
            "--num-companies",
            "500",
            "--output-dir",
            "custom/output",
            "--stdout",
            "--generator",
            "llm",
            "--model",
            "gpt-3.5-turbo",
            "--train-ratio",
            "0.8",
            "--val-ratio",
            "0.1",
            "--test-ratio",
            "0.1",
            "--random-seed",
            "123",
        ]

        with patch("sys.argv", ["generate_synthetic_data.py"] + test_args):
            args = parse_args()

            # Check custom values
            assert args.num_companies == 500
            assert args.output_dir == "custom/output"
            assert args.stdout is True
            assert args.generator == "llm"
            assert args.model == "gpt-3.5-turbo"
            assert args.train_ratio == 0.8
            assert args.val_ratio == 0.1
            assert args.test_ratio == 0.1
            assert args.random_seed == 123

    def test_invalid_generator(self):
        """Test that invalid generator raises error."""
        test_args = ["--generator", "invalid"]

        with patch("sys.argv", ["generate_synthetic_data.py"] + test_args):
            with pytest.raises(SystemExit):
                parse_args()

    def test_invalid_model(self):
        """Test that invalid model raises error."""
        test_args = ["--model", "invalid-model"]

        with patch("sys.argv", ["generate_synthetic_data.py"] + test_args):
            with pytest.raises(SystemExit):
                parse_args()
