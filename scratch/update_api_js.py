with open("frontend/js/api.js", "r", encoding="utf-8") as f:
    content = f.read()

target = """function formatDateTime(isoString) {
    if (!isoString) return "—";
    const d = new Date(isoString);
    if (Number.isNaN(d.getTime())) return String(isoString);
    return d.toLocaleString("vi-VN", {
        hour12: false,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
    });
}"""

replacement = """function formatDateTime(isoString) {
    if (!isoString) return "—";
    const s = String(isoString).replace(" ", "T");
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return String(isoString);
    return d.toLocaleString("vi-VN", {
        hour12: false,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
}"""

content_norm = content.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
replacement_norm = replacement.replace("\r\n", "\n")

if target_norm in content_norm:
    new_content = content_norm.replace(target_norm, replacement_norm)
    if "\r\n" in content:
        new_content = new_content.replace("\n", "\r\n")
    with open("frontend/js/api.js", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("SUCCESS: api.js updated")
else:
    print("FAILED: target not found")
