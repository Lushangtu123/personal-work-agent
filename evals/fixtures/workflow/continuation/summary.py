PRODUCT_LABEL = "My private inbox"


def category_summary(count):
    if count == 0:
        return "No suspicious categories detected."
    suffix = "y" if count == 1 else "ies"
    return f"{count} suspicious category{suffix} detected."
