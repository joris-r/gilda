import unicodedata


def name_key(name: str) -> str:
    """The key that sorts names alphabetically, ignoring case and accents."""
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))
