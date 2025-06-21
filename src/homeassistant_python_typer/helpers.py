def remove_common_indent_levels(text: str) -> str:
    if text.strip() == "":
        return ""
    lines = text.split("\n")
    common_indent = min(
        len(line) - len(line.lstrip()) for line in lines if line.strip() != ""
    )
    return "\n".join(line[common_indent:].rstrip() for line in lines)


def tab(text: str, n: int = 1) -> str:
    return "\n".join((f"{'    '*n}{line}" for line in text.split("\n")))


def retab(text: str, n: int = 1) -> str:
    return tab(remove_common_indent_levels(text), n)


def sanitize_for_ident(s: str) -> str:
    """
    Sanitize an identifier to ensure it is a valid to be used as part of a Python identifier.
    Replaces invalid characters with underscores
    """
    return "".join(char if char.isalnum() else "_" for char in s)


def sanitize_ident(s: str) -> str:
    """
    Sanitize an identifier to ensure it is a valid Python identifier.
    Replaces invalid characters with underscores and ensures it does not start with a digit.
    """
    sanitized = sanitize_for_ident(s)
    if sanitized and sanitized[0].isdigit():
        sanitized = "n" + sanitized
    return sanitized
