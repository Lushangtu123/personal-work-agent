from engine import parse_row


def parse_record(*, record):
    value = parse_row(record)
    return value["name"], value["count"]
