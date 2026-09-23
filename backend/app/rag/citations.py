"""Display real page numbers without inventing pages for text documents."""


def format_page(page: int | None) -> str:
    if isinstance(page, int) and not isinstance(page, bool) and page > 0:
        return f"第{page}页"
    return "页码不适用"
