def parse_lua_table(lua_content):
    print("parse_lua_table called with content length:", len(lua_content))
    import re

    annotations = []

    # Direct field extraction from entire content
    text_match = re.search(r'\["text"\] = "(.*?)"', lua_content, re.DOTALL)
    note_match = re.search(r'\["note"\] = "(.*?)"', lua_content, re.DOTALL)
    chapter_match = re.search(r'\["chapter"\] = "(.*?)"', lua_content, re.DOTALL)
    page_match = re.search(r'\["pageno"\] = (\d+)', lua_content)

    if text_match or note_match:
        annotation = {}
        if text_match:
            annotation["text"] = text_match.group(1).replace("\\n", " ").strip()
        if note_match:
            annotation["comment"] = note_match.group(1).replace("\\n", " ").strip()
        if chapter_match:
            annotation["chapter"] = chapter_match.group(1)
        if page_match:
            annotation["page"] = int(page_match.group(1))
        annotations.append(annotation)

    return annotations if annotations else None
