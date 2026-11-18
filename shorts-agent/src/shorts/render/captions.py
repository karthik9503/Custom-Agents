"""Captions: wrap, center, color the *starred* word, pop in."""

from PIL import Image, ImageDraw, ImageFont

from shorts.style import project_path

# A word is a list of (text, is_accent) runs, so "*yawn*?" keeps "?" in ink.
Run = tuple[str, bool]
Word = list[Run]


def parse_caption(caption: str) -> list[Word]:
    """Split a caption into words, tracking which characters were inside *stars*."""
    words: list[Word] = []
    current: Word = []
    accent = False
    buf = ""

    def flush_run() -> None:
        nonlocal buf
        if buf:
            current.append((buf, accent))
            buf = ""

    for ch in caption:
        if ch == "*":
            flush_run()
            accent = not accent
        elif ch.isspace():
            flush_run()
            if current:
                words.append(current)
                current = []
        else:
            buf += ch
    flush_run()
    if current:
        words.append(current)
    return words


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    full = project_path(path)
    if not full.exists():
        raise FileNotFoundError(f"Font not found: {full} (see README setup step 4)")
    return ImageFont.truetype(str(full), size)


def _word_width(font: ImageFont.FreeTypeFont, word: Word) -> float:
    return sum(font.getlength(text) for text, _ in word)


def wrap_words(words: list[Word], font: ImageFont.FreeTypeFont, max_width: float) -> list[list[Word]]:
    """Greedy line wrap. A single word wider than max_width gets its own line."""
    space = font.getlength(" ")
    lines: list[list[Word]] = []
    line: list[Word] = []
    width = 0.0
    for word in words:
        w = _word_width(font, word)
        needed = w if not line else width + space + w
        if line and needed > max_width:
            lines.append(line)
            line, width = [word], w
        else:
            line.append(word)
            width = needed
    if line:
        lines.append(line)
    return lines


def render_caption(
    caption: str,
    style: dict,
    max_width: float,
    ink: tuple[int, int, int],
    accent: tuple[int, int, int],
) -> Image.Image:
    """Render the caption block on a transparent layer (tightly cropped)."""
    cap = style["caption"]
    words = parse_caption(caption)

    # Shrink the font until it fits in max_lines, but never below the bubble size.
    size = cap["size_px"]
    min_size = style["bubble"]["size_px"]
    while True:
        font = load_font(cap["font"], size)
        lines = wrap_words(words, font, max_width)
        fits = len(lines) <= cap["max_lines"] and all(
            _line_width(font, ln) <= max_width for ln in lines
        )
        if fits or size <= min_size:
            break
        size = max(min_size, int(size * 0.9))

    ascent, descent = font.getmetrics()
    line_h = int((ascent + descent) * cap["line_spacing"])
    block_w = int(max(_line_width(font, ln) for ln in lines)) + 2
    block_h = line_h * (len(lines) - 1) + ascent + descent

    layer = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    space = font.getlength(" ")
    for i, line in enumerate(lines):
        x = (block_w - _line_width(font, line)) / 2
        y = i * line_h
        for j, word in enumerate(line):
            if j:
                x += space
            for text, is_accent in word:
                draw.text((x, y), text, font=font, fill=accent if is_accent else ink)
                x += font.getlength(text)
    return layer


def _line_width(font: ImageFont.FreeTypeFont, line: list[Word]) -> float:
    space = font.getlength(" ")
    return sum(_word_width(font, w) for w in line) + space * (len(line) - 1)


def pop_in_frames(layer: Image.Image, n_frames: int) -> list[Image.Image]:
    """Pre-render the pop-in: scale 90% -> 100% while fading in, over n_frames."""
    frames = []
    for i in range(n_frames):
        p = (i + 1) / (n_frames + 1)
        p = 1 - (1 - p) ** 2  # ease-out: fast start, gentle landing
        scale = 0.9 + 0.1 * p
        w = max(1, int(layer.width * scale))
        h = max(1, int(layer.height * scale))
        frame = layer.resize((w, h), Image.LANCZOS)
        alpha = frame.getchannel("A").point(lambda a: int(a * p))
        frame.putalpha(alpha)
        frames.append(frame)
    return frames
