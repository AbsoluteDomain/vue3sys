"""平台-认证模块。

"""

import random
import uuid
import base64
import logging
from io import BytesIO
from django.conf import settings
from django_redis import get_redis_connection


_logger = logging.getLogger(__name__)


def generate_captcha():
    """
    生成验证码图片，并将答案存入 Redis
    返回包含 captchaKey 和 captchaBase64 的字典
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ModuleNotFoundError as exc:
        _logger.exception("generate_captcha pillow_not_installed")
        raise RuntimeError("Captcha 功能需要安装 Pillow 依赖") from exc

    # 从 settings 获取配置
    captcha_timeout = getattr(
        settings,
        "CAPTCHA_EXPIRE_SECONDS",
        getattr(settings, "CAPTCHA_TIMEOUT", 300),
    )
    width = int(getattr(settings, "CAPTCHA_WIDTH", 120))
    height = int(getattr(settings, "CAPTCHA_HEIGHT", 40))
    font_size = int(getattr(settings, "CAPTCHA_FONT_SIZE", 28))
    font_weight = int(getattr(settings, "CAPTCHA_FONT_WEIGHT", 0))
    text_alpha = float(getattr(settings, "CAPTCHA_TEXT_ALPHA", 1.0))
    interference = int(
        getattr(
            settings,
            "CAPTCHA_INTERFERE_COUNT",
            getattr(settings, "CAPTCHA_INTERFERENCE", 2),
        )
    )

    code_type = getattr(settings, "CAPTCHA_CODE_TYPE", "")
    if not code_type:
        captcha_type = getattr(settings, "CAPTCHA_TYPE", "arithmetic")
        code_type = "math" if captcha_type in ["arithmetic", "math"] else "random"
    code_length = int(getattr(settings, "CAPTCHA_CODE_LENGTH", 4))

    font_path = getattr(settings, "CAPTCHA_FONT_PATH", "")

    _logger.info(
        "generate_captcha start code_type=%s captcha_timeout=%s interference=%s",
        code_type,
        captcha_timeout,
        interference,
    )

    # 初始化答案变量
    answer = ""
    render_segments = []

    # 根据验证码类型生成表达式和答案
    if str(code_type).lower() in ["math", "arithmetic"]:
        operator = random.choice(["+", "-", "*", "/"])
        if operator == "/":
            while True:
                b = random.randint(2, 9)
                max_q = 9 // b
                if max_q >= 1:
                    quotient = random.randint(1, max_q)
                    a = b * quotient
                    answer = str(quotient)
                    break
        else:
            a = random.randint(1, 9)
            b = random.randint(1, 9)
            if operator == "-":
                a, b = max(a, b), min(a, b)
                answer = str(a - b)
            elif operator == "+":
                answer = str(a + b)
            else:
                answer = str(a * b)

        display_operator = {"+": "+", "-": "-", "*": "×", "/": "÷"}[operator]
        expression = f"{a} {display_operator} {b} ="

        palette = [
            (233, 71, 106),
            (46, 204, 113),
            (52, 152, 219),
            (155, 89, 182),
            (243, 156, 18),
        ]
        prev_color = None
        for token in [str(a), display_operator, str(b), "="]:
            choices = [c for c in palette if c != prev_color] or palette
            color = random.choice(choices)
            render_segments.append((token, color))
            prev_color = color
    else:
        # 字母数字验证码：排除易混淆字符（0/O, 1/I/l）
        chars = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
        length = code_length if code_length > 0 else 4
        expression = "".join(random.choices(chars, k=length))
        answer = expression.lower()

        palette = [
            (233, 71, 106),
            (46, 204, 113),
            (52, 152, 219),
            (155, 89, 182),
            (243, 156, 18),
        ]
        prev_color = None
        for ch in expression:
            choices = [c for c in palette if c != prev_color] or palette
            color = random.choice(choices)
            render_segments.append((ch, color))
            prev_color = color

    # 创建验证码图片
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    font = None
    for candidate in [font_path, "arial.ttf", "DejaVuSans.ttf"]:
        if not candidate:
            continue
        try:
            font = ImageFont.truetype(candidate, font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    def _measure(draw_obj, text, use_stroke=True):
        try:
            bbox0 = draw_obj.textbbox(
                (0, 0),
                text,
                font=font,
                stroke_width=stroke_width if use_stroke else 0,
            )
        except TypeError:
            bbox0 = draw_obj.textbbox((0, 0), text, font=font)
        return bbox0[2] - bbox0[0], bbox0[3] - bbox0[1]

    # 使用 textbox 获取文字的边界框，计算文字宽度和高度
    stroke_width = 1 if font_weight == 1 else 0

    if render_segments:
        if str(code_type).lower() in ["math", "arithmetic"] and len(render_segments) == 4:
            segments_to_draw = [
                render_segments[0],
                (" ", None),
                render_segments[1],
                (" ", None),
                render_segments[2],
                (" ", None),
                render_segments[3],
            ]
        else:
            segments_to_draw = render_segments

        total_width = 0
        max_height = 0
        for seg_text, _seg_color in segments_to_draw:
            w0, h0 = _measure(draw, seg_text)
            total_width += w0
            max_height = max(max_height, h0)

        text_x = (width - total_width) / 2
        text_y = (height - max_height) / 2
        bbox = (
            0,
            0,
            int(total_width),
            int(max_height),
        )
    else:
        bbox = draw.textbbox((0, 0), expression, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (width - text_width) / 2
        text_y = (height - text_height) / 2

    if text_alpha < 1:
        overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        if render_segments:
            cursor_x = text_x
            for seg_text, seg_color in segments_to_draw:
                if seg_color is None:
                    w0, _h0 = _measure(overlay_draw, seg_text)
                    cursor_x += w0
                    continue
                fill_rgba = (
                    seg_color[0],
                    seg_color[1],
                    seg_color[2],
                    int(255 * max(0.0, min(1.0, text_alpha))),
                )
                try:
                    overlay_draw.text(
                        (cursor_x, text_y),
                        seg_text,
                        font=font,
                        fill=fill_rgba,
                        stroke_width=stroke_width,
                        stroke_fill=(80, 80, 80, fill_rgba[3]),
                    )
                except TypeError:
                    overlay_draw.text(
                        (cursor_x, text_y),
                        seg_text,
                        font=font,
                        fill=fill_rgba,
                    )
                w0, _h0 = _measure(overlay_draw, seg_text)
                cursor_x += w0
        else:
            text_color = (30, 30, 30)
            try:
                overlay_draw.text(
                    (text_x, text_y),
                    expression,
                    font=font,
                    fill=(text_color[0], text_color[1], text_color[2], int(255 * max(0.0, min(1.0, text_alpha)))),
                    stroke_width=stroke_width,
                    stroke_fill=(80, 80, 80, int(255 * max(0.0, min(1.0, text_alpha)))),
                )
            except TypeError:
                overlay_draw.text(
                    (text_x, text_y),
                    expression,
                    font=font,
                    fill=(text_color[0], text_color[1], text_color[2], int(255 * max(0.0, min(1.0, text_alpha)))),
                )

        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(image)
    else:
        if render_segments:
            cursor_x = text_x
            for seg_text, seg_color in segments_to_draw:
                if seg_color is None:
                    w0, _h0 = _measure(draw, seg_text)
                    cursor_x += w0
                    continue
                try:
                    draw.text(
                        (cursor_x, text_y),
                        seg_text,
                        font=font,
                        fill=seg_color,
                        stroke_width=stroke_width,
                        stroke_fill=(80, 80, 80),
                    )
                except TypeError:
                    draw.text((cursor_x, text_y), seg_text, font=font, fill=seg_color)
                w0, _h0 = _measure(draw, seg_text)
                cursor_x += w0
        else:
            text_color = (30, 30, 30)
            try:
                draw.text(
                    (text_x, text_y),
                    expression,
                    font=font,
                    fill=text_color,
                    stroke_width=stroke_width,
                    stroke_fill=(80, 80, 80),
                )
            except TypeError:
                draw.text((text_x, text_y), expression, font=font, fill=text_color)

    text_rect = (
        int(text_x + bbox[0]) - 2,
        int(text_y + bbox[1]) - 2,
        int(text_x + bbox[2]) + 2,
        int(text_y + bbox[3]) + 2,
    )

    # 边框
    draw.rectangle([0, 0, width - 1, height - 1], outline=(220, 220, 220))

    # 添加轻量干扰（浅灰色，避免遮挡文字）
    line_color = (185, 185, 185)
    for _ in range(max(0, interference)):
        start = None
        end = None
        for __ in range(12):
            candidate_start = (random.randint(0, width - 1), random.randint(0, height - 1))
            candidate_end = (random.randint(0, width - 1), random.randint(0, height - 1))
            line_bbox = (
                min(candidate_start[0], candidate_end[0]),
                min(candidate_start[1], candidate_end[1]),
                max(candidate_start[0], candidate_end[0]),
                max(candidate_start[1], candidate_end[1]),
            )
            if (
                line_bbox[2] < text_rect[0]
                or line_bbox[0] > text_rect[2]
                or line_bbox[3] < text_rect[1]
                or line_bbox[1] > text_rect[3]
            ):
                start = candidate_start
                end = candidate_end
                break
        if start is not None and end is not None:
            draw.line([start, end], fill=line_color, width=1)

    point_color = (205, 205, 205)
    for _ in range(max(0, interference) * 8):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        if text_rect[0] <= x <= text_rect[2] and text_rect[1] <= y <= text_rect[3]:
            continue
        draw.point((x, y), fill=point_color)

    # 将图片保存到内存并转为 Base64 编码
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    captcha_base64 = f"data:image/png;base64,{img_base64}"

    # 生成唯一的 captchaKey，并将答案存入 Redis
    captcha_id = uuid.uuid4().hex
    redis_conn = get_redis_connection("default")
    try:
        redis_conn.setex(captcha_id, captcha_timeout, answer)
        _logger.info("generate_captcha success captcha_id=%s", captcha_id)
    except Exception as e:
        _logger.exception("generate_captcha redis_write_failed captcha_id=%s", captcha_id)

    return {
        "captchaId": captcha_id,
        "captchaBase64": captcha_base64
    }
