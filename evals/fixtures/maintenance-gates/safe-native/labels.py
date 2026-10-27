def summarize(count):
    if count == 0:
        return "No labels"
    return f"{count} {'label' if count == 1 else 'labels'}"
