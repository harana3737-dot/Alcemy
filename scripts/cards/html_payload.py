"""Встроенные блоки данных для автономных HTML."""
import base64
import json
from pathlib import Path
import re
import zlib

HERE = Path(__file__).resolve().parent
FORMAT = "alcemy-deflate"
BLOCK = re.compile(r'\["alcemy-deflate",[^\]\r\n]*\]')


def compressed_text(text):
    raw = text.encode("utf-8")
    encoder = zlib.compressobj(level=9, wbits=-zlib.MAX_WBITS)
    compressed = encoder.compress(raw) + encoder.flush()
    return json.dumps([FORMAT, len(raw), base64.b64encode(compressed).decode("ascii")], separators=(",", ":"))


def compressed_json(value):
    return compressed_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def embedded_texts(page):
    """Проверки комплектов читают содержимое сжатых блоков."""
    for block in BLOCK.finditer(page):
        _, size, encoded = json.loads(block[0])
        raw = zlib.decompress(base64.b64decode(encoded, validate=True), wbits=-zlib.MAX_WBITS)
        if len(raw) != size:
            raise ValueError("Повреждён встроенный блок данных")
        yield raw.decode("utf-8")


def payload_reader():
    vendor = HERE / "vendor" / "tiny-inflate"
    license_text = (vendor / "LICENSE").read_text(encoding="utf-8")
    inflate = (vendor / "index.js").read_text(encoding="utf-8")
    reader = (HERE / "html_payload.js").read_text(encoding="utf-8")
    return (
        "/* tiny-inflate 1.0.3 (https://www.npmjs.com/package/tiny-inflate/v/1.0.3)\n"
        + license_text + "*/\n"
        + "const inflateHtmlPayload=(()=>{const module={exports:null};\n"
        + inflate + "return module.exports;})();\n"
        + reader
    )
