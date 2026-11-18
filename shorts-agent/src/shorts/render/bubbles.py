"""Speech bubbles: a rounded rectangle with a tail pointing at the speaker's head."""

from PIL import Image, ImageDraw

from shorts.render.captions import load_font


def _wrap_text(text: str, font, max_width: float) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and font.getlength(candidate) > max_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def render_bubble(
    text: str,
    style: dict,
    max_width: float,
    fill: tuple[int, int, int],
    ink: tuple[int, int, int],
    tail_offset: float = 0.0,
) -> tuple[Image.Image, int]:
    """Render the bubble body + a downward tail on a transparent layer.

    `tail_offset` moves the tail sideways from the center, in output pixels
    (used when the bubble is shifted to stay inside the safe zone).
    Returns (layer, tail_height).
    """
    b = style["bubble"]
    ss = style["figure"]["supersample"]
    font = load_font(b["font"], b["size_px"] * ss)
    pad = b["padding_px"] * ss
    radius = b["radius_px"] * ss
    outline = max(2, style["figure"]["line_width"] // 2) * ss
    tail_h = b["padding_px"] * ss
    tail_w = b["padding_px"] * ss

    text = text[: b["max_chars"]]
    lines = _wrap_text(text, font, max_width * ss - 2 * pad)
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    text_w = max(font.getlength(ln) for ln in lines)
    body_w = int(text_w + 2 * pad)
    body_h = int(line_h * len(lines) + 2 * pad)

    w, h = body_w + outline * 2, body_h + tail_h + outline * 2
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    x0, y0 = outline, outline
    x1, y1 = x0 + body_w, y0 + body_h
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=ink, width=outline)

    # Tail: filled triangle that covers the body's bottom border, then two edges.
    # Keep the tail clear of the rounded corners.
    limit = body_w / 2 - radius - tail_w / 2
    cx = w / 2 + max(-limit, min(limit, tail_offset * ss))
    tip = (cx, h - outline)
    left = (cx - tail_w / 2, y1 - outline)
    right = (cx + tail_w / 2, y1 - outline)
    draw.polygon([left, right, tip], fill=fill)
    draw.line([(left[0], y1), tip], fill=ink, width=outline)
    draw.line([(right[0], y1), tip], fill=ink, width=outline)

    for i, line in enumerate(lines):
        draw.text((w / 2, y0 + pad + i * line_h), line, font=font, fill=ink, anchor="ma")

    small = layer.resize((w // ss, h // ss), Image.LANCZOS)
    return small, tail_h // ss
