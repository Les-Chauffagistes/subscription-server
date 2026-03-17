from urllib.parse import parse_qs


def parse_urlencoded(raw: str) -> dict:
    parsed = parse_qs(raw, keep_blank_values=True)
    return {key: values[0] if len(values) == 1 else values for key, values in parsed.items()}
