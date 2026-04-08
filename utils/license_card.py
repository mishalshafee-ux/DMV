from __future__ import annotations

import io

import qrcode
from PIL import Image, ImageDraw, ImageFont

from config import settings


def generate_license_card(
    username: str,
    license_type: str,
    issue_date: str,
    card_uuid: str,
) -> io.BytesIO:
    card = Image.new("RGB", (900, 520), (19, 28, 45))
    draw = ImageDraw.Draw(card)
    font_big = ImageFont.load_default()
    font_small = ImageFont.load_default()

    draw.rounded_rectangle((20, 20, 880, 500), radius=28, outline=(78, 160, 255), width=4, fill=(29, 39, 62))
    draw.text((48, 42), "STATE DMV DIGITAL LICENSE", fill=(255, 255, 255), font=font_big)
    draw.text((48, 110), f"Name: {username}", fill=(230, 236, 245), font=font_small)
    draw.text((48, 160), f"License Type: {license_type}", fill=(230, 236, 245), font=font_small)
    draw.text((48, 210), f"Issue Date: {issue_date[:10]}", fill=(230, 236, 245), font=font_small)
    draw.text((48, 260), f"Card ID: {card_uuid}", fill=(230, 236, 245), font=font_small)
    draw.text((48, 390), "Scan QR to verify on dashboard", fill=(135, 188, 255), font=font_small)

    qr_url = f"{settings.web_base_url}/license/{card_uuid}"
    qr = qrcode.make(qr_url).resize((220, 220))
    card.paste(qr, (620, 135))

    buffer = io.BytesIO()
    card.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
