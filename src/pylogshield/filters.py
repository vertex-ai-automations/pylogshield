from __future__ import annotations

import logging
from typing import Iterable, List, Optional, Sequence, Tuple


class KeywordFilter(logging.Filter):
    """Filter log records based on keywords in the message.

    This filter can either include only messages containing specific keywords
    or exclude messages containing those keywords.

    Parameters
    ----------
    keywords : Iterable[str]
        Iterable of keywords to test against the log message.
    include : bool, optional
        If True, only records containing any keyword are allowed.
        If False, records containing any keyword are excluded. Default is True.
    case_insensitive : bool, optional
        Whether to match keywords case-insensitively. Default is True.
    name : str, optional
        The filter name. Default is empty string.

    Examples
    --------
    >>> # Include only logs containing "error" or "critical"
    >>> filter = KeywordFilter(["error", "critical"], include=True)
    >>> handler.addFilter(filter)

    >>> # Exclude logs containing "debug" or "trace"
    >>> filter = KeywordFilter(["debug", "trace"], include=False)
    """

    def __init__(
        self,
        keywords: Iterable[str],
        *,
        include: bool = True,
        case_insensitive: bool = True,
        name: str = "",
    ) -> None:
        super().__init__(name)
        self.include = include
        self.case_insensitive = case_insensitive
        kws: List[str] = [k for k in keywords if k]
        self.keywords: Sequence[str] = tuple(
            (k.lower() if case_insensitive else k) for k in kws
        )

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.keywords:
            return True
        msg = record.getMessage()
        haystack = msg.lower() if self.case_insensitive else msg
        hit = any(k in haystack for k in self.keywords)
        return hit if self.include else (not hit)

    def __repr__(self) -> str:
        mode = "include" if self.include else "exclude"
        return f"{self.__class__.__name__}(keywords={list(self.keywords)}, mode={mode})"


class ContextScrubber(logging.Filter):
    """Strip potentially sensitive environment-derived attributes from LogRecord.

    This filter removes attributes from log records that might contain cloud provider
    credentials or tokens that were inadvertently added to the logging context.

    The filter always returns True (allowing the record through) after scrubbing
    the sensitive attributes.

    Parameters
    ----------
    forbidden_prefixes : tuple of str or None, optional
        Tuple of attribute name prefixes to scrub. Default is None, which uses
        the default cloud provider prefixes.
    name : str, optional
        The filter name. Default is empty string.

    Attributes
    ----------
    DEFAULT_FORBIDDEN_PREFIXES : tuple of str
        Default prefixes to scrub: AWS_, AZURE_, GCP_, GOOGLE_, TOKEN.

    Notes
    -----
    The following prefixes are scrubbed by default:

    - ``AWS_`` - Amazon Web Services credentials
    - ``AZURE_`` - Microsoft Azure credentials
    - ``GCP_`` - Google Cloud Platform credentials
    - ``GOOGLE_`` - Google services credentials
    - ``TOKEN`` - Various token attributes

    Examples
    --------
    >>> scrubber = ContextScrubber()
    >>> handler.addFilter(scrubber)

    >>> # Custom prefixes
    >>> scrubber = ContextScrubber(forbidden_prefixes=("SECRET_", "PRIVATE_"))
    """

    DEFAULT_FORBIDDEN_PREFIXES = ("AWS_", "AZURE_", "GCP_", "GOOGLE_", "TOKEN")

    def __init__(
        self, forbidden_prefixes: Optional[Tuple[str, ...]] = None, name: str = ""
    ) -> None:
        super().__init__(name)
        self._forbidden_prefixes = forbidden_prefixes or self.DEFAULT_FORBIDDEN_PREFIXES

    def filter(self, record: logging.LogRecord) -> bool:
        for k in list(record.__dict__.keys()):
            if isinstance(k, str) and k.upper().startswith(self._forbidden_prefixes):
                record.__dict__.pop(k, None)
        extra = record.__dict__.get("extra", None)
        if isinstance(extra, dict):
            record.__dict__["extra"] = {
                k: v for k, v in extra.items()
                if not str(k).upper().startswith(self._forbidden_prefixes)
            }
        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(prefixes={self._forbidden_prefixes})"
