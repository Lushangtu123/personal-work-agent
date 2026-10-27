PRODUCT_LABEL = "Inbox preview"


def category_summary(count):
    """Summarize a non-negative integer category count."""
    if count == 0:
        return "No suspicious categories detected."
    suffix = "y" if count == 1 else "ies"
    return f"{count} suspicious category{suffix} detected."
