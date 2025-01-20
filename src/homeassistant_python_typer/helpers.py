def remove_common_indent_levels(text: str) -> str:
    if text.strip() == "":
        return ""
    lines = text.split("\n")
    common_indent = min(
        len(line) - len(line.lstrip()) for line in lines if line.strip() != ""
    )
    return "\n".join(line[common_indent:].rstrip() for line in lines)


def tab(text: str, n: int = 1) -> str:
    return "\n".join((f"{"    "*n}{line}" for line in text.split("\n")))


def retab(text: str, n: int = 1) -> str:
    return tab(remove_common_indent_levels(text), n)
