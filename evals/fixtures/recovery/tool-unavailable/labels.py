def label(name):
    value = name.strip()
    if not value:
        raise ValueError("name must not be empty")
    return value
