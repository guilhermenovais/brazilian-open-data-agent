"""testset_runner's per-package exception hierarchy (contracts/errors.md).

Mirrors dataset_selector.exceptions'/data_access.exceptions's own base-exception
pattern: one base class, one subclass per whole-run/whole-comparison failure.
"""


class TestsetRunnerError(Exception):
    """Base class for every exception this package raises."""


class TestsetLoadError(TestsetRunnerError):
    """A testset file could not be loaded: missing, unreadable, invalid JSON, a
    record missing a required field, or a duplicate `n` value."""


class RunLoadError(TestsetRunnerError):
    """A saved run file could not be loaded: missing path, or invalid content."""


class IncompatibleRunsError(TestsetRunnerError):
    """Two runs being compared were not made from the same testset content."""
