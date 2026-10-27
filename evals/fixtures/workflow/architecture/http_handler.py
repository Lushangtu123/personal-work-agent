from engine import parse_row


def upload_text(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) > 25:
        raise ValueError("batch too large")
    return [parse_row(line) for line in lines]
