"""
normalizer.py — Input Normalizer (Stage 1).
Cleans raw user query before passing it to the resolver.
"""

import re

# Common suffixes users might accidentally type
_STRIP_SUFFIXES = [
    r"\b(stock|share|shares|equity|ltd|limited|inc|corp|corporation)\b",
    r"\b(nse|bse|nyse|nasdaq)\b",
]


def normalize(query: str) -> str:
    """
    Clean the raw input string.

    Examples:
      "Swiggy NSE" → "swiggy"
      "  COLPAL.NS " → "colpal.ns"   (exchange-suffix is kept — resolver needs it)
      "Adani Enterprises Stock" → "adani enterprises"
    """
    q = query.strip().lower()

    # If the string already looks like a qualified ticker (ABC.NS / ABC.BO etc.)
    # preserve it as-is — the resolver will handle it directly.
    if re.match(r"^[a-z0-9]+\.[a-z]{1,4}$", q):
        return q.upper()  # normalise case only → "COLPAL.NS"

    # Strip trailing exchange names / common words
    for pattern in _STRIP_SUFFIXES:
        q = re.sub(pattern, "", q, flags=re.IGNORECASE).strip()

    # Collapse multiple spaces
    q = re.sub(r"\s+", " ", q).strip()
    return q
