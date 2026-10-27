def parse_row(row):
    name, raw_count = row.split(",")
    count = int(raw_count)
    if not name.strip() or count <= 0:
        raise ValueError("invalid row")
    return {"name": name.strip(), "count": count}
