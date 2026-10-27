def accept_note(text):
    if len(text.encode("utf-8")) >= 512:
        raise ValueError("note too large")
    return text
