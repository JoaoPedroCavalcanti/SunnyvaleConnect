"""QR code PNG encoder abstraction."""

import io
from abc import ABC, abstractmethod

import qrcode
from PIL import Image

_QR_PIXEL_SIZE = 200


class IQRCodeEncoder(ABC):
    @abstractmethod
    def encode_png(self, payload: str) -> bytes: ...


class QRCodeEncoder(IQRCodeEncoder):
    def encode_png(self, payload: str) -> bytes:
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        image = image.resize((_QR_PIXEL_SIZE, _QR_PIXEL_SIZE), Image.NEAREST)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
