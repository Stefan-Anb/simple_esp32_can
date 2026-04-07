#!/usr/bin/env python3
"""
CAN Monitor — PyQt6 + python-can
Supports all python-can interfaces: slcan (serial + TCP), socketcan, pcan, kvaser, …
"""

import sys
import json
import struct
import time
import threading
from datetime import datetime
from typing import Optional

import can
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSettings, QSize
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QFontDatabase, QIcon,
    QSyntaxHighlighter, QTextCharFormat
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QSplitter, QTabWidget, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QScrollArea, QFrame, QGroupBox,
    QSpinBox, QDialog, QDialogButtonBox, QFileDialog, QMessageBox,
    QSizePolicy, QAbstractItemView, QStatusBar, QToolBar,
    QFormLayout, QSpacerItem
)

# ─────────────────────────────────────────────────────────
#  COLOUR PALETTE
# ─────────────────────────────────────────────────────────
C = {
    "bg0":          "#090b0f",
    "bg1":          "#0d1117",
    "bg2":          "#131920",
    "bg3":          "#1a2230",
    "border":       "#1e2d40",
    "border_br":    "#2a4060",
    "accent":       "#00d4ff",
    "accent2":      "#00ff9d",
    "accent4":      "#c084fc",
    "text":         "#c9d1d9",
    "text_dim":     "#4a6080",
    "text_br":      "#e6edf3",
    "danger":       "#ff4444",
    "warn":         "#ffaa00",
    "ok":           "#00ff9d",
}

STYLESHEET = f"""
QWidget {{
    background-color: {C['bg0']};
    color: {C['text']};
    font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
    font-size: 13px;
}}
QMainWindow {{
    background-color: {C['bg0']};
}}
QTabWidget::pane {{
    border: 1px solid {C['border']};
    background: {C['bg0']};
    top: -1px;
}}
QTabBar::tab {{
    background: {C['bg1']};
    color: {C['text_dim']};
    padding: 8px 22px;
    border: 1px solid {C['border']};
    border-bottom: none;
    font-size: 11px;
    letter-spacing: 1px;
}}
QTabBar::tab:selected {{
    background: {C['bg0']};
    color: {C['accent']};
    border-bottom: 2px solid {C['accent']};
}}
QTabBar::tab:hover {{ color: {C['text_br']}; }}

QPushButton {{
    background: transparent;
    color: {C['text']};
    border: 1px solid {C['border_br']};
    padding: 6px 16px;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 11px;
    letter-spacing: 1px;
    min-height: 28px;
}}
QPushButton:hover {{
    background: {C['bg3']};
    border-color: {C['accent']};
    color: {C['accent']};
}}
QPushButton:disabled {{
    color: {C['text_dim']};
    border-color: {C['border']};
}}
QPushButton#primary {{
    border-color: {C['accent']};
    color: {C['accent']};
}}
QPushButton#primary:hover {{ background: rgba(0,212,255,0.12); }}
QPushButton#success {{
    border-color: {C['accent2']};
    color: {C['accent2']};
}}
QPushButton#success:hover {{ background: rgba(0,255,157,0.12); }}
QPushButton#danger {{
    border-color: {C['danger']};
    color: {C['danger']};
}}
QPushButton#danger:hover {{ background: rgba(255,68,68,0.12); }}
QPushButton#warn {{
    border-color: {C['warn']};
    color: {C['warn']};
}}
QPushButton#warn:hover {{ background: rgba(255,170,0,0.12); }}

QLineEdit, QSpinBox {{
    background: {C['bg2']};
    border: 1px solid {C['border']};
    color: {C['text_br']};
    padding: 5px 10px;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 13px;
    min-height: 28px;
}}
QLineEdit:focus, QSpinBox:focus {{
    border-color: {C['accent']};
    background: {C['bg3']};
}}
QLineEdit::placeholder {{ color: {C['text_dim']}; }}

QComboBox {{
    background: {C['bg2']};
    border: 1px solid {C['border']};
    color: {C['text_br']};
    padding: 5px 10px;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 13px;
    min-height: 28px;
}}
QComboBox:focus {{ border-color: {C['accent']}; }}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    width: 10px; height: 10px;
}}
QComboBox QAbstractItemView {{
    background: {C['bg2']};
    color: {C['text']};
    selection-background-color: {C['bg3']};
    border: 1px solid {C['border_br']};
    padding: 2px;
    font-size: 13px;
}}

QTableWidget {{
    background: {C['bg0']};
    gridline-color: transparent;
    border: none;
    color: {C['text']};
    font-size: 12px;
}}
QTableWidget::item {{
    padding: 3px 8px;
    border-bottom: 1px solid {C['border']};
    background: transparent;
}}
QTableWidget::item:selected {{
    background: {C['bg3']};
    color: {C['text_br']};
}}
QHeaderView::section {{
    background: {C['bg1']};
    color: {C['text_dim']};
    border: none;
    border-bottom: 1px solid {C['border_br']};
    border-right: 1px solid {C['border']};
    padding: 5px 8px;
    font-size: 10px;
    letter-spacing: 1.5px;
}}

QScrollBar:vertical {{
    background: {C['bg1']};
    width: 8px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {C['border_br']};
    min-height: 30px;
    border-radius: 4px;
    margin: 1px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C['text_dim']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0; background: none; border: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QScrollBar:horizontal {{
    background: {C['bg1']};
    height: 8px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {C['border_br']};
    min-width: 30px;
    border-radius: 4px;
    margin: 1px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; background: none; border: none;
}}

QCheckBox {{
    color: {C['text']};
    spacing: 8px;
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {C['border_br']};
    background: {C['bg2']};
    border-radius: 2px;
}}
QCheckBox::indicator:checked {{
    background: {C['accent']};
    border-color: {C['accent']};
}}

QSplitter::handle {{
    background: {C['border']};
}}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}

QStatusBar {{
    background: {C['bg1']};
    border-top: 1px solid {C['border']};
    color: {C['text_dim']};
    font-size: 11px;
}}
QStatusBar::item {{ border: none; }}

QDialog {{
    background: {C['bg1']};
}}
QMessageBox {{
    background: {C['bg1']};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background: {C['bg3']};
    border: none;
    width: 16px;
}}
"""


# ─────────────────────────────────────────────────────────
#  CONFIGURABLE PARSER ENGINE
# ─────────────────────────────────────────────────────────
#
#  A ParserDef describes one logical signal group:
#  {
#    "name":       "Cell Voltages #0",
#    "can_id":     "0x2900",
#    "can_mask":   "0xFFFFFF00",        # optional, default 0xFFFFFFFF
#    "mux_byte":   0,                   # optional: byte index used as mux discriminator
#    "mux_value":  0,                   # optional: expected value at mux_byte (after & mux_mask)
#    "mux_mask":   "0xFF",              # optional, default 0xFF
#    "fields": [
#      {
#        "name":   "Cell 0",
#        "offset": 2,                   # byte offset in data
#        "length": 2,                   # byte length (1/2/4)
#        "type":   "i16be",             # u8/i8/u16be/u16le/i16be/i16le/u32be/u32le/i32be/i32le/f32be/f32le
#        "scale":  0.001,               # multiply raw value
#        "add":    0,                   # add after scale
#        "unit":   "V",
#        "fmt":    ".3f"                # python format spec
#      }
#    ]
#  }
#
#  The deduplicate key in LogTab/LiveTab is (can_id, parser_name) so multiplexed
#  variants of the same CAN ID each get their own row/card.

import copy

FIELD_TYPES = ["u8","i8","u16be","u16le","i16be","i16le","u32be","u32le","i32be","i32le","f32be","f32le"]

_STRUCT_FMT = {
    "u8":    (">B", 1), "i8":    (">b", 1),
    "u16be": (">H", 2), "u16le": ("<H", 2),
    "i16be": (">h", 2), "i16le": ("<h", 2),
    "u32be": (">I", 4), "u32le": ("<I", 4),
    "i32be": (">i", 4), "i32le": ("<i", 4),
    "f32be": (">f", 4), "f32le": ("<f", 4),
}

def _decode_field(data: bytes, field: dict):
    off   = int(field.get("offset", 0))
    ftype = field.get("type", "u8")
    fmt, size = _STRUCT_FMT.get(ftype, (">B", 1))
    if off + size > len(data):
        return None
    raw = struct.unpack_from(fmt, data, off)[0]
    scale = float(field.get("scale", 1))
    add   = float(field.get("add",   0))
    val   = raw * scale + add
    fmt_s = field.get("fmt", "g")
    try:
        return format(val, fmt_s)
    except Exception:
        return str(val)

def _match_parser(pdef: dict, arb_id: int, data: bytes) -> bool:
    """Return True if this parser definition matches the given frame."""
    try:
        base = int(pdef["can_id"], 16)
        mask = int(pdef.get("can_mask", "0xFFFFFFFF"), 16)
        if (arb_id & mask) != (base & mask):
            return False
        if "mux_byte" in pdef:
            mb   = int(pdef["mux_byte"])
            mv   = int(pdef.get("mux_value", 0))
            mm   = int(pdef.get("mux_mask", "0xFF"), 16)
            if mb >= len(data):
                return False
            if (data[mb] & mm) != (mv & mm):
                return False
        return True
    except Exception:
        return False

def apply_parsers(parsers: list, arb_id: int, data: bytes):
    """
    Returns list of (parser_name, mux_key, fields_dict) for all matching parsers.
    mux_key is used as part of the deduplicate key.
    fields_dict: {field_name: (formatted_value_str, unit_str)}
    """
    results = []
    for pdef in parsers:
        if not _match_parser(pdef, arb_id, data):
            continue
        fields = {}
        for f in pdef.get("fields", []):
            val = _decode_field(data, f)
            if val is not None:
                fields[f.get("name", "?")] = (val, f.get("unit", ""))
        mux_key = str(pdef.get("mux_value", "")) if "mux_byte" in pdef else ""
        results.append((pdef["name"], mux_key, fields))
    return results

# ── Built-in default parsers (converted to the new dict format) ──────────────
BUILTIN_PARSERS = [
    {
        "name": "BMS Voltage", "can_id": "0x2600", "can_mask": "0xFFFFFF00",
        "fields": [
            {"name": "Pack V", "offset": 0, "length": 4, "type": "f32be", "scale": 1, "add": 0, "unit": "V",  "fmt": ".2f"},
            {"name": "Out V",  "offset": 4, "length": 4, "type": "f32be", "scale": 1, "add": 0, "unit": "V",  "fmt": ".2f"},
        ]
    },
    {
        "name": "BMS Current", "can_id": "0x2700", "can_mask": "0xFFFFFF00",
        "fields": [
            {"name": "Current", "offset": 0, "length": 4, "type": "f32be", "scale": 1, "add": 0, "unit": "A", "fmt": ".2f"},
        ]
    },
    {
        "name": "BMS Energy", "can_id": "0x2800", "can_mask": "0xFFFFFF00",
        "fields": [
            {"name": "Cap",    "offset": 0, "length": 4, "type": "f32be", "scale": 1, "add": 0, "unit": "Ah", "fmt": ".3f"},
            {"name": "Energy", "offset": 4, "length": 4, "type": "f32be", "scale": 1, "add": 0, "unit": "Wh", "fmt": ".3f"},
        ]
    },
    {
        "name": "Total Charge", "can_id": "0x3500", "can_mask": "0xFFFFFF00",
        "fields": [
            {"name": "Tot Chg", "offset": 0, "length": 4, "type": "f32be", "scale": 1, "add": 0, "unit": "Ah", "fmt": ".1f"},
            {"name": "Tot En",  "offset": 4, "length": 4, "type": "f32be", "scale": 1, "add": 0, "unit": "Wh", "fmt": ".1f"},
        ]
    },
    {
        "name": "Total Discharge", "can_id": "0x3600", "can_mask": "0xFFFFFF00",
        "fields": [
            {"name": "Tot Dsg", "offset": 0, "length": 4, "type": "f32be", "scale": 1, "add": 0, "unit": "Ah", "fmt": ".1f"},
            {"name": "Tot En",  "offset": 4, "length": 4, "type": "f32be", "scale": 1, "add": 0, "unit": "Wh", "fmt": ".1f"},
        ]
    },
    # Cell voltages — multiplexed by byte 0 (start index)
    {
        "name": "Cell V (idx 0)", "can_id": "0x2900", "can_mask": "0xFFFFFF00",
        "mux_byte": 0, "mux_value": 0, "mux_mask": "0xFF",
        "fields": [
            {"name": "Cell 0", "offset": 2, "length": 2, "type": "i16be", "scale": 0.001, "add": 0, "unit": "V", "fmt": ".3f"},
            {"name": "Cell 1", "offset": 4, "length": 2, "type": "i16be", "scale": 0.001, "add": 0, "unit": "V", "fmt": ".3f"},
            {"name": "Cell 2", "offset": 6, "length": 2, "type": "i16be", "scale": 0.001, "add": 0, "unit": "V", "fmt": ".3f"},
        ]
    },
    {
        "name": "Cell V (idx 3)", "can_id": "0x2900", "can_mask": "0xFFFFFF00",
        "mux_byte": 0, "mux_value": 3, "mux_mask": "0xFF",
        "fields": [
            {"name": "Cell 3", "offset": 2, "length": 2, "type": "i16be", "scale": 0.001, "add": 0, "unit": "V", "fmt": ".3f"},
            {"name": "Cell 4", "offset": 4, "length": 2, "type": "i16be", "scale": 0.001, "add": 0, "unit": "V", "fmt": ".3f"},
            {"name": "Cell 5", "offset": 6, "length": 2, "type": "i16be", "scale": 0.001, "add": 0, "unit": "V", "fmt": ".3f"},
        ]
    },
    {
        "name": "Balancing", "can_id": "0x2A00", "can_mask": "0xFFFFFF00",
        "fields": [
            {"name": "Mask", "offset": 6, "length": 2, "type": "u16be", "scale": 1, "add": 0, "unit": "bin", "fmt": "016b"},
        ]
    },
    {
        "name": "BMS Status", "can_id": "0x2D00", "can_mask": "0xFFFFFF00",
        "fields": [
            {"name": "Min V",    "offset": 0, "length": 2, "type": "i16be", "scale": 0.001, "add": 0, "unit": "V",  "fmt": ".3f"},
            {"name": "Max V",    "offset": 2, "length": 2, "type": "i16be", "scale": 0.001, "add": 0, "unit": "V",  "fmt": ".3f"},
            {"name": "SOC",      "offset": 4, "length": 1, "type": "u8",    "scale": 0.392, "add": 0, "unit": "%",  "fmt": ".1f"},
            {"name": "SOH",      "offset": 5, "length": 1, "type": "u8",    "scale": 0.392, "add": 0, "unit": "%",  "fmt": ".1f"},
            {"name": "Max Temp", "offset": 6, "length": 1, "type": "u8",    "scale": 1,     "add": 0, "unit": "°C", "fmt": "d"},
        ]
    },
    {
        "name": "Environment", "can_id": "0x2C00", "can_mask": "0xFFFFFF00",
        "fields": [
            {"name": "T-BME", "offset": 0, "length": 2, "type": "i16be", "scale": 0.01,  "add": 0, "unit": "°C", "fmt": ".1f"},
            {"name": "Hum",   "offset": 2, "length": 2, "type": "i16be", "scale": 0.01,  "add": 0, "unit": "%",  "fmt": ".1f"},
            {"name": "T-FET", "offset": 4, "length": 2, "type": "i16be", "scale": 0.01,  "add": 0, "unit": "°C", "fmt": ".1f"},
            {"name": "Press", "offset": 6, "length": 2, "type": "i16be", "scale": 10.0,  "add": 0, "unit": "Pa", "fmt": ".0f"},
        ]
    },
    {
        "name": "Charger Message", "can_id": "0x18FF50E5", "can_mask": "0xFFFFFFFF",
        "fields": [
            {"name": "Voltage", "offset": 0, "length": 2, "type": "i16be", "scale": 0.1, "add": 0, "unit": "V",  "fmt": ".1f"},
            {"name": "Current", "offset": 2, "length": 2, "type": "i16be", "scale": 0.1, "add": 0, "unit": "A",  "fmt": ".1f"},
            {"name": "Status",  "offset": 4, "length": 1, "type": "u8",    "scale": 1,   "add": 0, "unit": "",   "fmt": "d"},
            {"name": "Temp",    "offset": 5, "length": 1, "type": "u8",    "scale": 1,   "add": 0, "unit": "°C", "fmt": "d"},
        ]
    },
    {
        "name": "Charger Command", "can_id": "0x1806E5F4", "can_mask": "0xFFFFFFFF",
        "fields": [
            {"name": "Voltage", "offset": 0, "length": 2, "type": "i16be", "scale": 0.1, "add": 0, "unit": "V", "fmt": ".1f"},
            {"name": "Current", "offset": 2, "length": 2, "type": "i16be", "scale": 0.1, "add": 0, "unit": "A", "fmt": ".1f"},
            {"name": "Control", "offset": 4, "length": 1, "type": "u8",    "scale": 1,   "add": 0, "unit": "",  "fmt": "d"},
        ]
    },
    {
        "name": "Current Sensor", "can_id": "0x0301", "can_mask": "0xFFFFFFFF",
        "fields": [
            {"name": "Current", "offset": 2, "length": 4, "type": "i32be", "scale": 1, "add": 0, "unit": "mA", "fmt": "d"},
        ]
    },
]

# Global mutable parser list — modified by ParserTab at runtime
ACTIVE_PARSERS: list = copy.deepcopy(BUILTIN_PARSERS)


# ─────────────────────────────────────────────────────────
#  CAN RECEIVER THREAD
# ─────────────────────────────────────────────────────────
class CANWorker(QThread):
    frame_received = pyqtSignal(object)   # emits can.Message
    error_occurred = pyqtSignal(str)
    connected      = pyqtSignal()
    disconnected   = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.bus: Optional[can.BusABC] = None
        self._stop = threading.Event()

    def connect(self, interface: str, channel: str, bitrate: int, extra: dict):
        self._stop.clear()
        self._interface = interface
        self._channel   = channel
        self._bitrate   = bitrate
        self._extra     = extra
        self.start()

    def disconnect(self):
        self._stop.set()

    def run(self):
        try:
            kwargs = dict(
                interface = self._interface,
                channel   = self._channel,
                bitrate   = self._bitrate,
                **self._extra
            )
            # slcan needs timing differently
            if self._interface == "slcan":
                kwargs.pop("bitrate", None)
                kwargs["ttyBaudrate"] = self._extra.get("ttyBaudrate", 115200)
                kwargs["bitrate"]     = self._bitrate
            self.bus = can.interface.Bus(**kwargs)
            self.connected.emit()
        except Exception as e:
            self.error_occurred.emit(f"Verbindungsfehler: {e}")
            return

        while not self._stop.is_set():
            try:
                msg = self.bus.recv(timeout=0.1)
                if msg is not None:
                    self.frame_received.emit(msg)
            except can.CanError as e:
                self.error_occurred.emit(f"CAN Fehler: {e}")
                break
            except Exception as e:
                self.error_occurred.emit(f"Fehler: {e}")
                break

        try:
            if self.bus:
                self.bus.shutdown()
                self.bus = None
        except Exception:
            pass
        self.disconnected.emit()

    def send(self, msg: can.Message):
        if self.bus:
            try:
                self.bus.send(msg)
                return True
            except Exception as e:
                self.error_occurred.emit(f"Sendefehler: {e}")
        return False


# ─────────────────────────────────────────────────────────
#  TASK RUNNER
# ─────────────────────────────────────────────────────────
class SendTask:
    def __init__(self, name: str, interval_ms: int, frames: list):
        self.name        = name
        self.interval_ms = interval_ms
        self.frames      = frames   # list of dicts: {id, data, is_ext}
        self.running     = False
        self.count       = 0
        self._timer: Optional[QTimer] = None

    def start(self, send_fn):
        if self.running:
            return
        self.running = True
        self._timer = QTimer()
        self._timer.setInterval(self.interval_ms)
        self._timer.timeout.connect(lambda: self._fire(send_fn))
        self._timer.start()

    def stop(self):
        self.running = False
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _fire(self, send_fn):
        for f in self.frames:
            try:
                arb_id = int(f["id"], 16)
                raw    = bytes.fromhex(f["data"].replace(" ", ""))
                msg    = can.Message(
                    arbitration_id = arb_id,
                    data           = raw,
                    is_extended_id = f.get("is_ext", True)
                )
                send_fn(msg)
                self.count += 1
            except Exception:
                pass

    def to_dict(self):
        return {"name": self.name, "interval": self.interval_ms, "frames": self.frames}

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["interval"], d["frames"])


# ─────────────────────────────────────────────────────────
#  HELPER WIDGETS
# ─────────────────────────────────────────────────────────
def make_label(text, style=None):
    lbl = QLabel(text)
    if style == "heading":
        lbl.setStyleSheet(
            f"color: {C['accent']}; font-size: 11px; letter-spacing: 2px; background: transparent; border: none;"
        )
    elif style == "dim":
        lbl.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 12px; background: transparent; border: none;"
        )
    return lbl

def make_btn(text, style=None):
    btn = QPushButton(text)
    btn.setMinimumHeight(28)
    if style == "primary":
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['accent']}; border: 1px solid {C['accent']}; "
            f"padding: 6px 16px; font-size: 11px; min-height: 28px; }}"
            f"QPushButton:hover {{ background: rgba(0,212,255,0.12); }}"
            f"QPushButton:disabled {{ color: {C['text_dim']}; border-color: {C['border']}; }}"
        )
    elif style == "success":
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['accent2']}; border: 1px solid {C['accent2']}; "
            f"padding: 6px 16px; font-size: 11px; min-height: 28px; }}"
            f"QPushButton:hover {{ background: rgba(0,255,157,0.12); }}"
            f"QPushButton:disabled {{ color: {C['text_dim']}; border-color: {C['border']}; }}"
        )
    elif style == "danger":
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['danger']}; border: 1px solid {C['danger']}; "
            f"padding: 6px 16px; font-size: 11px; min-height: 28px; }}"
            f"QPushButton:hover {{ background: rgba(255,68,68,0.12); }}"
        )
    elif style == "warn":
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['warn']}; border: 1px solid {C['warn']}; "
            f"padding: 6px 16px; font-size: 11px; min-height: 28px; }}"
            f"QPushButton:hover {{ background: rgba(255,170,0,0.12); }}"
        )
    return btn

def h_sep():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color: {C['border']}; background: {C['border']}; border: none; max-height: 1px;")
    return f

def v_sep():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet(f"color: {C['border']}; background: {C['border']}; border: none; max-width: 1px;")
    return f


# ─────────────────────────────────────────────────────────
#  CONNECT DIALOG
# ─────────────────────────────────────────────────────────
class ConnectDialog(QDialog):
    INTERFACES = [
        ("slcan (Serial/TCP)",  "slcan"),
        ("socketcan (Linux)",   "socketcan"),
        ("PCAN",                "pcan"),
        ("Kvaser",              "kvaser"),
        ("Vector",              "vector"),
        ("IXXAT",               "ixxat"),
        ("Virtual (Test)",      "virtual"),
    ]
    BAUDRATES = [1000000, 800000, 500000, 250000, 125000, 100000, 50000, 20000, 10000]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Interface verbinden")
        self.setMinimumWidth(420)
        self.settings = QSettings("CANMonitor", "CANMonitor")
        self._build()
        self._restore()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        # Interface selector
        self.combo_iface = QComboBox()
        for label, _ in self.INTERFACES:
            self.combo_iface.addItem(label)
        self.combo_iface.currentIndexChanged.connect(self._update_hints)
        form.addRow(make_label("Interface:", "dim"), self.combo_iface)

        # Channel
        self.edit_channel = QLineEdit()
        self.edit_channel.setPlaceholderText("z.B. /dev/ttyUSB0  oder  192.168.1.1:23")
        form.addRow(make_label("Channel:", "dim"), self.edit_channel)

        # Baudrate
        self.combo_baud = QComboBox()
        for b in self.BAUDRATES:
            self.combo_baud.addItem(f"{b//1000}k  ({b})", b)
        self.combo_baud.setCurrentIndex(2)  # 500k default
        form.addRow(make_label("CAN Baudrate:", "dim"), self.combo_baud)

        # slcan tty baud (only relevant for serial slcan)
        self.combo_tty_baud = QComboBox()
        for b in [115200, 500000, 1000000, 57600, 38400]:
            self.combo_tty_baud.addItem(str(b), b)
        form.addRow(make_label("Serial Baud:", "dim"), self.combo_tty_baud)
        self._tty_baud_row = form.itemAt(form.rowCount()-1, QFormLayout.ItemRole.FieldRole)

        layout.addLayout(form)

        # Hint label
        self.hint_label = QLabel()
        self.hint_label.setObjectName("dim")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        layout.addWidget(h_sep())

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Verbinden")
        btns.button(QDialogButtonBox.StandardButton.Ok).setObjectName("success")
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._update_hints()

    def _update_hints(self):
        _, iface = self.INTERFACES[self.combo_iface.currentIndex()]
        hints = {
            "slcan":     "Serial: /dev/ttyUSB0  |  TCP: socket://192.168.1.1:23",
            "socketcan": "Linux SocketCAN: can0, vcan0, …",
            "pcan":      "PCAN: PCAN_USBBUS1, PCAN_USBBUS2, …",
            "kvaser":    "Kvaser: 0, 1, 2, …",
            "vector":    "Vector: 0, 1, …  (XL-Driver benötigt)",
            "ixxat":     "IXXAT: 0, 1, …",
            "virtual":   "Kein echtes Interface nötig (Test)",
        }
        self.hint_label.setText(hints.get(iface, ""))
        # Show tty baud only for slcan
        show_tty = (iface == "slcan")
        # find the label for tty row
        form = self.layout().itemAt(0).layout()
        for i in range(form.rowCount()):
            item_label = form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            item_field = form.itemAt(i, QFormLayout.ItemRole.FieldRole)
            if item_label and "Serial Baud" in item_label.widget().text():
                item_label.widget().setVisible(show_tty)
                item_field.widget().setVisible(show_tty)

    def _accept(self):
        self._save()
        self.accept()

    def _save(self):
        s = self.settings
        s.setValue("iface_index",    self.combo_iface.currentIndex())
        s.setValue("channel",        self.edit_channel.text())
        s.setValue("baud_index",     self.combo_baud.currentIndex())
        s.setValue("tty_baud_index", self.combo_tty_baud.currentIndex())

    def _restore(self):
        s = self.settings
        self.combo_iface.setCurrentIndex(int(s.value("iface_index", 0)))
        self.edit_channel.setText(s.value("channel", ""))
        self.combo_baud.setCurrentIndex(int(s.value("baud_index", 2)))
        self.combo_tty_baud.setCurrentIndex(int(s.value("tty_baud_index", 0)))

    def get_params(self):
        _, iface = self.INTERFACES[self.combo_iface.currentIndex()]
        channel  = self.edit_channel.text().strip()
        bitrate  = self.combo_baud.currentData()
        extra    = {}
        if iface == "slcan":
            extra["ttyBaudrate"] = self.combo_tty_baud.currentData()
        return iface, channel, bitrate, extra


# ─────────────────────────────────────────────────────────
#  TASK EDITOR DIALOG
# ─────────────────────────────────────────────────────────
class TaskDialog(QDialog):
    def __init__(self, task: Optional[SendTask] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sendetask")
        self.setMinimumWidth(560)
        self._frames = []
        self._build()
        if task:
            self._load(task)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        form = QFormLayout()
        self.edit_name     = QLineEdit(); self.edit_name.setPlaceholderText("Task Name")
        self.spin_interval = QSpinBox();  self.spin_interval.setRange(10, 60000); self.spin_interval.setValue(100); self.spin_interval.setSuffix(" ms")
        form.addRow(make_label("Name:", "dim"),     self.edit_name)
        form.addRow(make_label("Intervall:", "dim"), self.spin_interval)
        layout.addLayout(form)

        layout.addWidget(h_sep())

        # Frame list header
        hdr = QHBoxLayout()
        hdr.addWidget(make_label("FRAMES", "heading"))
        hdr.addStretch()
        add_btn = make_btn("+ Frame")
        add_btn.clicked.connect(self._add_frame_row)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        # Frame table
        self.frame_table = QTableWidget(0, 4)
        self.frame_table.setHorizontalHeaderLabels(["CAN-ID (Hex)", "Daten (Hex)", "Typ", ""])
        self.frame_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.frame_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.frame_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.frame_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.frame_table.setColumnWidth(0, 130)
        self.frame_table.setColumnWidth(2, 80)
        self.frame_table.setColumnWidth(3, 32)
        self.frame_table.verticalHeader().setVisible(False)
        self.frame_table.setMinimumHeight(160)
        layout.addWidget(self.frame_table)

        layout.addWidget(h_sep())

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Speichern")
        btns.button(QDialogButtonBox.StandardButton.Ok).setObjectName("success")
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _add_frame_row(self, frame=None):
        row = self.frame_table.rowCount()
        self.frame_table.insertRow(row)
        self.frame_table.setRowHeight(row, 28)

        id_edit   = QLineEdit(frame["id"]   if frame else ""); id_edit.setPlaceholderText("0x18FF50E5")
        data_edit = QLineEdit(frame["data"] if frame else ""); data_edit.setPlaceholderText("AA BB CC DD")
        combo = QComboBox(); combo.addItems(["Extended", "Standard"])
        if frame and not frame.get("is_ext", True):
            combo.setCurrentIndex(1)

        del_btn = make_btn("✕"); del_btn.setObjectName("danger")
        del_btn.setFixedSize(28, 24)
        del_btn.clicked.connect(lambda: self.frame_table.removeRow(self.frame_table.currentRow() or row))

        self.frame_table.setCellWidget(row, 0, id_edit)
        self.frame_table.setCellWidget(row, 1, data_edit)
        self.frame_table.setCellWidget(row, 2, combo)
        self.frame_table.setCellWidget(row, 3, del_btn)

    def _load(self, task: SendTask):
        self.edit_name.setText(task.name)
        self.spin_interval.setValue(task.interval_ms)
        for f in task.frames:
            self._add_frame_row(f)

    def _accept(self):
        if not self.edit_name.text().strip():
            QMessageBox.warning(self, "Fehler", "Name darf nicht leer sein.")
            return
        self.accept()

    def get_task(self, existing: Optional[SendTask] = None) -> SendTask:
        frames = []
        for row in range(self.frame_table.rowCount()):
            id_w   = self.frame_table.cellWidget(row, 0)
            data_w = self.frame_table.cellWidget(row, 1)
            type_w = self.frame_table.cellWidget(row, 2)
            frames.append({
                "id":     id_w.text().strip(),
                "data":   data_w.text().strip(),
                "is_ext": type_w.currentIndex() == 0,
            })
        if existing:
            existing.stop()
            existing.name        = self.edit_name.text().strip()
            existing.interval_ms = self.spin_interval.value()
            existing.frames      = frames
            return existing
        return SendTask(self.edit_name.text().strip(), self.spin_interval.value(), frames)


# ─────────────────────────────────────────────────────────
#  LOG TAB
# ─────────────────────────────────────────────────────────
class LogTab(QWidget):
    MAX_ROWS = 2000

    def __init__(self):
        super().__init__()
        self._paused    = False
        self._dedupe    = True   # default ON
        self._id_rows   = {}     # (arb_id, parser_name, mux_key) → row index
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QWidget(); bar.setStyleSheet(f"background:{C['bg1']}; border-bottom:1px solid {C['border']};")
        bl  = QHBoxLayout(bar); bl.setContentsMargins(8, 4, 8, 4); bl.setSpacing(6)

        self.filter_edit = QLineEdit(); self.filter_edit.setPlaceholderText("Filter ID / Name …")
        self.filter_edit.setMaximumWidth(200)
        self.filter_edit.textChanged.connect(self._apply_filter)

        self.chk_autoscroll = QCheckBox("Auto-Scroll"); self.chk_autoscroll.setChecked(True)
        self.chk_dedupe     = QCheckBox("Deduplizieren"); self.chk_dedupe.setChecked(True)
        self.chk_dedupe.toggled.connect(self._on_dedupe_toggle)
        self.btn_pause  = make_btn("Pause");  self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_clear  = make_btn("Clear");  self.btn_clear.clicked.connect(self.clear)

        bl.addWidget(self.filter_edit)
        bl.addWidget(self.chk_autoscroll)
        bl.addWidget(self.chk_dedupe)
        bl.addStretch()
        bl.addWidget(self.btn_pause)
        bl.addWidget(self.btn_clear)
        layout.addWidget(bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "ID", "Typ", "Rohdaten", "Geparst"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 105)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 50)
        self.table.setColumnWidth(3, 180)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)

    def _on_dedupe_toggle(self, checked):
        self._dedupe = checked
        if not checked:
            self._id_rows.clear()

    def _toggle_pause(self):
        self._paused = not self._paused
        self.btn_pause.setText("Fortsetzen" if self._paused else "Pause")
        if self._paused:
            self.btn_pause.setStyleSheet(
                f"QPushButton {{ background: rgba(255,170,0,0.15); color: {C['warn']}; border: 1px solid {C['warn']}; padding: 6px 16px; font-size: 11px; min-height: 28px; }}"
            )
        else:
            self.btn_pause.setStyleSheet("")

    def clear(self):
        self.table.setRowCount(0)
        self._id_rows.clear()

    def _apply_filter(self, text):
        text = text.lower()
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 1)
            parsed_item = self.table.item(row, 4)
            match = (not text
                     or text in (id_item.text() if id_item else "").lower()
                     or text in (parsed_item.text() if parsed_item else "").lower())
            self.table.setRowHidden(row, not match)

    def append(self, msg: can.Message, parsed_name: str, mux_key: str, parsed_data: dict):
        if self._paused:
            return

        ts      = datetime.fromtimestamp(msg.timestamp).strftime("%H:%M:%S.%f")[:12]
        id_str  = f"0x{msg.arbitration_id:08X}" if msg.is_extended_id else f"0x{msg.arbitration_id:03X}"
        typ     = "EXT" if msg.is_extended_id else "STD"
        raw     = " ".join(f"{b:02X}" for b in msg.data)
        parsed  = ""
        if parsed_data:
            parsed = "  ".join(f"{k}: {v} {u}".strip() for k, (v, u) in parsed_data.items())
        elif parsed_name:
            parsed = f"[{parsed_name}]"

        filt = self.filter_edit.text().lower()
        if filt and filt not in id_str.lower() and filt not in parsed.lower() and filt not in (parsed_name or "").lower():
            return

        dedupe_key = (msg.arbitration_id, parsed_name or "", mux_key)

        if self._dedupe and dedupe_key in self._id_rows:
            row = self._id_rows[dedupe_key]
            self._set_row(row, ts, id_str, typ, raw, parsed_name, parsed)
            return

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 24)
        self._set_row(row, ts, id_str, typ, raw, parsed_name, parsed)

        if self._dedupe:
            self._id_rows[dedupe_key] = row

        while self.table.rowCount() > self.MAX_ROWS:
            self.table.removeRow(0)
            self._id_rows = {k: v-1 for k, v in self._id_rows.items() if v > 0}

        if self.chk_autoscroll.isChecked():
            self.table.scrollToBottom()

    def _set_row(self, row, ts, id_str, typ, raw, parsed_name, parsed):
        def item(text, color=None):
            it = QTableWidgetItem(text)
            if color:
                it.setForeground(QColor(color))
            return it

        self.table.setItem(row, 0, item(ts,     C["text_dim"]))
        self.table.setItem(row, 1, item(id_str, C["accent"]))
        self.table.setItem(row, 2, item(typ,    C["accent4"] if typ == "EXT" else C["accent"]))
        self.table.setItem(row, 3, item(raw,    C["text_dim"]))
        full = f"[{parsed_name}]  {parsed}" if parsed_name and parsed else (parsed or raw)
        it = item(full, C["accent2"] if parsed_name else C["text_dim"])
        self.table.setItem(row, 4, it)


# ─────────────────────────────────────────────────────────
#  LIVE VIEW TAB
# ─────────────────────────────────────────────────────────
class LiveCard(QFrame):
    CARD_W = 240
    CARD_H = 200   # fixed height keeps grid uniform

    def __init__(self, arb_id: int, name: str, is_ext: bool):
        super().__init__()
        self._arb_id = arb_id
        self._is_ext = is_ext
        self.setFixedWidth(self.CARD_W)
        self.setMinimumHeight(self.CARD_H)
        self.setStyleSheet(
            f"LiveCard {{ background-color: {C['bg2']}; border: 1px solid {C['border_br']}; }}"
        )
        self._build(arb_id, name, is_ext)

    def _build(self, arb_id, name, is_ext):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(0)

        id_str = f"0x{arb_id:08X}" if is_ext else f"0x{arb_id:03X}"

        # ── Header ──────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 6)

        self.name_lbl = QLabel(name or "Unknown")
        self.name_lbl.setStyleSheet(
            f"color: {C['accent4']}; font-size: 11px; font-weight: bold; background: transparent; border: none;"
        )
        self.name_lbl.setMaximumWidth(140)

        self.id_lbl = QLabel(id_str)
        self.id_lbl.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 11px; background: transparent; border: none;"
        )
        self.id_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        hdr.addWidget(self.name_lbl, 1)
        hdr.addWidget(self.id_lbl, 0)
        layout.addLayout(hdr)

        # ── Separator ───────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C['border']}; background: {C['border']}; border: none; max-height: 1px; margin-bottom: 6px;")
        layout.addWidget(sep)

        # ── KV area — use a single QLabel with HTML for simplicity ──
        self.kv_lbl = QLabel()
        self.kv_lbl.setStyleSheet(f"color: {C['text']}; font-size: 12px; background: transparent; border: none;")
        self.kv_lbl.setWordWrap(True)
        self.kv_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.kv_lbl, 1)

        # ── Timestamp ───────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C['border']}; background: {C['border']}; border: none; max-height: 1px; margin-top: 4px;")
        layout.addWidget(sep2)

        self.ts_lbl = QLabel("")
        self.ts_lbl.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 10px; background: transparent; border: none; margin-top: 4px;"
        )
        self.ts_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.ts_lbl)

    def update_data(self, msg: can.Message, parsed_name: str, parsed_data: dict):
        raw = " ".join(f"{b:02X}" for b in msg.data)

        if parsed_data:
            lines = []
            for k, (v, u) in parsed_data.items():
                val_str = f"{v} {u}".strip()
                lines.append(
                    f'<span style="color:{C["text_dim"]}">{k}: </span>'
                    f'<span style="color:{C["accent2"]}; font-weight:bold">{val_str}</span>'
                )
            self.kv_lbl.setText("<br>".join(lines))
        else:
            self.kv_lbl.setText(f'<span style="color:{C["text_dim"]}">{raw}</span>')

        ts = datetime.fromtimestamp(msg.timestamp).strftime("%H:%M:%S.%f")[:12]
        self.ts_lbl.setText(f"{ts}  ·  DLC {msg.dlc}")

        # Flash only the ID text (no border change)
        self.id_lbl.setStyleSheet(
            f"color: {C['accent2']}; font-size: 11px; font-weight: bold; background: transparent; border: none;"
        )
        QTimer.singleShot(500, self._reset_id_style)

    def _reset_id_style(self):
        self.id_lbl.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 11px; background: transparent; border: none;"
        )


class LiveTab(QWidget):
    def __init__(self):
        super().__init__()
        self._cards = {}   # arb_id → LiveCard
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QWidget()
        bar.setStyleSheet(f"background:{C['bg1']}; border-bottom:1px solid {C['border']};")
        bl = QHBoxLayout(bar); bl.setContentsMargins(10, 6, 10, 6)
        bl.addWidget(make_label("Letzter Stand je CAN-ID", "dim"))
        bl.addStretch()
        clr = make_btn("Clear"); clr.clicked.connect(self.clear)
        bl.addWidget(clr)
        layout.addWidget(bar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._container = QWidget()
        self._container.setStyleSheet(f"background: {C['bg0']};")
        self._flow = QGridLayout(self._container)
        self._flow.setContentsMargins(10, 10, 10, 10)
        self._flow.setSpacing(8)
        self._flow.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

    def clear(self):
        for card in self._cards.values():
            card.deleteLater()
        self._cards.clear()

    def update(self, msg: can.Message, parsed_name: str, mux_key: str, parsed_data: dict):
        # Card key = (arb_id, parser_name) so muxed variants get separate cards
        card_key = (msg.arbitration_id, parsed_name or "", mux_key)
        if card_key not in self._cards:
            card = LiveCard(msg.arbitration_id, parsed_name, msg.is_extended_id)
            self._cards[card_key] = card
            idx = len(self._cards) - 1
            cols = max(1, self._scroll.viewport().width() // (LiveCard.CARD_W + 8))
            self._flow.addWidget(card, idx // cols, idx % cols)
        self._cards[card_key].update_data(msg, parsed_name, parsed_data)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reflow cards on resize
        if not self._cards:
            return
        cols = max(1, self.width() // (LiveCard.CARD_W + 8))
        for i, card in enumerate(self._cards.values()):
            self._flow.addWidget(card, i // cols, i % cols)


# ─────────────────────────────────────────────────────────
#  SEND TAB
# ─────────────────────────────────────────────────────────
class SendTab(QWidget):
    send_requested = pyqtSignal(object)   # emits can.Message

    def __init__(self):
        super().__init__()
        self._history = []
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Top: send form in a fixed-height panel
        top = QWidget()
        top.setStyleSheet(f"background: {C['bg1']}; border-bottom: 1px solid {C['border']};")
        top_l = QVBoxLayout(top)
        top_l.setContentsMargins(16, 14, 16, 14)
        top_l.setSpacing(10)

        top_l.addWidget(make_label("EINZELPAKET SENDEN", "heading"))

        form = QFormLayout(); form.setSpacing(8); form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.edit_id   = QLineEdit(); self.edit_id.setPlaceholderText("z.B. 0x18FF50E5")
        self.edit_data = QLineEdit(); self.edit_data.setPlaceholderText("z.B. 0A 1B 2C 3D")
        self.combo_typ = QComboBox(); self.combo_typ.addItems(["Extended", "Standard"])
        form.addRow(make_label("CAN-ID (Hex):", "dim"), self.edit_id)
        form.addRow(make_label("Daten (Hex):", "dim"),  self.edit_data)
        form.addRow(make_label("Typ:", "dim"),           self.combo_typ)
        top_l.addLayout(form)

        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self.btn_send = make_btn("▶  Senden", "success")
        self.btn_send.setMinimumWidth(120)
        self.btn_send.clicked.connect(self._send)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color: {C['accent2']}; font-size: 12px;")
        btn_row.addWidget(self.btn_send)
        btn_row.addWidget(self.status_lbl)
        btn_row.addStretch()
        top_l.addLayout(btn_row)

        outer.addWidget(top)

        # Bottom: history fills the rest
        bot = QWidget()
        bot_l = QVBoxLayout(bot)
        bot_l.setContentsMargins(16, 10, 16, 10)
        bot_l.setSpacing(6)

        hdr_row = QHBoxLayout()
        hdr_row.addWidget(make_label("ZULETZT GESENDET", "heading"))
        hdr_row.addWidget(make_label("(Doppelklick = Wiederverwenden)", "dim"))
        hdr_row.addStretch()
        bot_l.addLayout(hdr_row)

        self.history_table = QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["ID", "Daten", "Typ"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.history_table.setColumnWidth(0, 130)
        self.history_table.setColumnWidth(2, 70)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.cellDoubleClicked.connect(self._recall)
        bot_l.addWidget(self.history_table, 1)  # stretch=1 → fills space

        outer.addWidget(bot, 1)  # stretch=1 → history panel grows

    def _send(self):
        try:
            arb_id = int(self.edit_id.text().strip(), 16)
            data   = bytes.fromhex(self.edit_data.text().replace(" ", ""))
            is_ext = self.combo_typ.currentIndex() == 0
            msg    = can.Message(arbitration_id=arb_id, data=data, is_extended_id=is_ext)
            self.send_requested.emit(msg)
            self._push_history(arb_id, data, is_ext)
            self.status_lbl.setText(f"✓ Gesendet")
            QTimer.singleShot(1500, lambda: self.status_lbl.setText(""))
        except Exception as e:
            self.status_lbl.setText(f"Fehler: {e}")
            self.status_lbl.setStyleSheet(f"color:{C['danger']};")
            QTimer.singleShot(2000, lambda: (
                self.status_lbl.setText(""),
                self.status_lbl.setStyleSheet(f"color:{C['accent2']};")
            ))

    def _push_history(self, arb_id, data, is_ext):
        id_str  = f"{'0x%08X' % arb_id if is_ext else '0x%03X' % arb_id}"
        raw     = " ".join(f"{b:02X}" for b in data)
        typ     = "EXT" if is_ext else "STD"
        self._history.insert(0, (id_str, raw, typ))
        if len(self._history) > 20:
            self._history.pop()
        self._refresh_history()

    def _refresh_history(self):
        self.history_table.setRowCount(0)
        for id_str, raw, typ in self._history:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            self.history_table.setRowHeight(row, 22)
            self.history_table.setItem(row, 0, QTableWidgetItem(id_str))
            self.history_table.setItem(row, 1, QTableWidgetItem(raw))
            self.history_table.setItem(row, 2, QTableWidgetItem(typ))

    def _recall(self, row, _col):
        if row < len(self._history):
            id_str, raw, typ = self._history[row]
            self.edit_id.setText(id_str)
            self.edit_data.setText(raw)
            self.combo_typ.setCurrentIndex(0 if typ == "EXT" else 1)

    def prefill(self, id_str, data_str, is_ext):
        self.edit_id.setText(id_str)
        self.edit_data.setText(data_str)
        self.combo_typ.setCurrentIndex(0 if is_ext else 1)


# ─────────────────────────────────────────────────────────
#  TASKS TAB
# ─────────────────────────────────────────────────────────
class TaskRow(QFrame):
    toggled          = pyqtSignal(object)
    edit_requested   = pyqtSignal(object)
    delete_requested = pyqtSignal(object)

    def __init__(self, task: SendTask):
        super().__init__()
        self.task = task
        self._build()
        self._refresh_state()

    def _build(self):
        self.setMinimumHeight(90)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # ── Header ──────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(10)
        self.dot = QLabel("●"); self.dot.setFixedWidth(14)
        self.name_lbl = QLabel(self.task.name)
        self.name_lbl.setStyleSheet(
            f"color: {C['text_br']}; font-size: 13px; font-weight: bold; background: transparent; border: none;"
        )
        self.int_lbl = QLabel(f"{self.task.interval_ms} ms")
        self.int_lbl.setStyleSheet(
            f"color: {C['accent']}; font-size: 12px; background: transparent; border: none;"
        )
        self.count_lbl = QLabel("0×")
        self.count_lbl.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 11px; background: transparent; border: none;"
        )
        hdr.addWidget(self.dot)
        hdr.addWidget(self.name_lbl, 1)
        hdr.addWidget(self.int_lbl)
        hdr.addWidget(self.count_lbl)
        layout.addLayout(hdr)

        # ── Frame preview ───────────────────────────────
        self.preview_lbl = QLabel()
        self.preview_lbl.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 11px; background: transparent; border: none;"
        )
        self._update_preview()
        layout.addWidget(self.preview_lbl)

        # ── Buttons ─────────────────────────────────────
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_row.setContentsMargins(0, 2, 0, 0)

        self.btn_toggle = QPushButton("▶  Starten")
        self.btn_edit   = QPushButton("✎  Bearbeiten")
        self.btn_del    = QPushButton("✕  Löschen")

        for btn in (self.btn_toggle, self.btn_edit, self.btn_del):
            btn.setMinimumHeight(28)
            btn.setMinimumWidth(100)

        self.btn_toggle.clicked.connect(lambda: self.toggled.emit(self.task))
        self.btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.task))
        self.btn_del.clicked.connect(lambda: self.delete_requested.emit(self.task))

        btn_row.addWidget(self.btn_toggle)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_del)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _update_preview(self):
        parts = [f"{f['id']} [{f['data']}]" for f in self.task.frames[:3]]
        if len(self.task.frames) > 3:
            parts.append(f"… +{len(self.task.frames)-3}")
        self.preview_lbl.setText("  ·  ".join(parts))

    def _refresh_state(self):
        if self.task.running:
            self.dot.setStyleSheet(f"color: {C['ok']}; font-size: 10px; background: transparent; border: none;")
            self.btn_toggle.setText("■  Stoppen")
            self.btn_toggle.setStyleSheet(
                f"background: transparent; color: {C['danger']}; border: 1px solid {C['danger']}; "
                f"padding: 6px 16px; font-size: 11px; min-height: 28px; min-width: 100px;"
            )
            self.setStyleSheet(
                f"TaskRow {{ background-color: {C['bg2']}; border: 1px solid {C['accent2']}; }}"
            )
        else:
            self.dot.setStyleSheet(f"color: {C['danger']}; font-size: 10px; background: transparent; border: none;")
            self.btn_toggle.setText("▶  Starten")
            self.btn_toggle.setStyleSheet(
                f"background: transparent; color: {C['accent2']}; border: 1px solid {C['accent2']}; "
                f"padding: 6px 16px; font-size: 11px; min-height: 28px; min-width: 100px;"
            )
            self.setStyleSheet(
                f"TaskRow {{ background-color: {C['bg2']}; border: 1px solid {C['border']}; }}"
            )
        self.btn_edit.setStyleSheet(
            f"background: transparent; color: {C['text']}; border: 1px solid {C['border_br']}; "
            f"padding: 6px 16px; font-size: 11px; min-height: 28px; min-width: 100px;"
        )
        self.btn_del.setStyleSheet(
            f"background: transparent; color: {C['danger']}; border: 1px solid {C['danger']}; "
            f"padding: 6px 16px; font-size: 11px; min-height: 28px; min-width: 100px;"
        )

    def refresh(self):
        self.name_lbl.setText(self.task.name)
        self.int_lbl.setText(f"{self.task.interval_ms} ms")
        self.count_lbl.setText(f"{self.task.count}×")
        self._update_preview()
        self._refresh_state()


class TasksTab(QWidget):
    send_requested = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.tasks: list[SendTask] = []
        self._rows:  list[TaskRow] = []
        self._build()
        self._tick = QTimer(); self._tick.timeout.connect(self._refresh_counts)
        self._tick.start(500)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QWidget(); bar.setStyleSheet(f"background:{C['bg1']}; border-bottom:1px solid {C['border']};")
        bl  = QHBoxLayout(bar); bl.setContentsMargins(8, 4, 8, 4); bl.setSpacing(6)
        btn_start = make_btn("▶ Alle starten", "success"); btn_start.clicked.connect(self._start_all)
        btn_stop  = make_btn("■ Alle stoppen", "danger");  btn_stop.clicked.connect(self._stop_all)
        btn_new   = make_btn("+ Neuer Task",   "primary"); btn_new.clicked.connect(self._new_task)
        btn_exp   = make_btn("Export JSON");  btn_exp.clicked.connect(self._export)
        btn_imp   = make_btn("Import JSON");  btn_imp.clicked.connect(self._import)
        bl.addWidget(btn_start); bl.addWidget(btn_stop)
        bl.addStretch()
        bl.addWidget(btn_new); bl.addWidget(btn_exp); bl.addWidget(btn_imp)
        layout.addWidget(bar)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._container = QWidget()
        self._container.setStyleSheet(f"background: {C['bg0']};")
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setContentsMargins(10, 10, 10, 10)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()
        self._empty_lbl = QLabel("Keine Sendetasks.\nErstelle einen neuen Task oder importiere eine Konfiguration.")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 13px; background: transparent; border: none;")
        self._list_layout.insertWidget(0, self._empty_lbl)
        scroll.setWidget(self._container)
        layout.addWidget(scroll)

    def _refresh_counts(self):
        for row in self._rows:
            row.count_lbl.setText(f"{row.task.count}×")

    def _add_row(self, task: SendTask):
        row = TaskRow(task)
        row.toggled.connect(self._toggle_task)
        row.edit_requested.connect(self._edit_task)
        row.delete_requested.connect(self._delete_task)
        self._rows.append(row)
        self._list_layout.insertWidget(self._list_layout.count() - 1, row)
        self._empty_lbl.setVisible(False)

    def _new_task(self):
        dlg = TaskDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            task = dlg.get_task()
            self.tasks.append(task)
            self._add_row(task)

    def _edit_task(self, task: SendTask):
        row = next((r for r in self._rows if r.task is task), None)
        dlg = TaskDialog(task=task, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.get_task(existing=task)
            if row:
                row.refresh()

    def _delete_task(self, task: SendTask):
        task.stop()
        row = next((r for r in self._rows if r.task is task), None)
        if row:
            self._list_layout.removeWidget(row)
            row.deleteLater()
            self._rows.remove(row)
        self.tasks.remove(task)
        self._empty_lbl.setVisible(len(self.tasks) == 0)

    def _toggle_task(self, task: SendTask):
        if task.running:
            task.stop()
        else:
            task.start(lambda msg: self.send_requested.emit(msg))
        row = next((r for r in self._rows if r.task is task), None)
        if row:
            row.refresh()

    def _start_all(self):
        for task in self.tasks:
            if not task.running:
                task.start(lambda msg: self.send_requested.emit(msg))
        for row in self._rows:
            row.refresh()

    def _stop_all(self):
        for task in self.tasks:
            task.stop()
        for row in self._rows:
            row.refresh()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Tasks exportieren", "tasks.json", "JSON (*.json)")
        if path:
            with open(path, "w") as f:
                json.dump([t.to_dict() for t in self.tasks], f, indent=2)

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Tasks importieren", "", "JSON (*.json)")
        if path:
            with open(path) as f:
                data = json.load(f)
            self._stop_all()
            for r in list(self._rows):
                self._list_layout.removeWidget(r); r.deleteLater()
            self._rows.clear(); self.tasks.clear()
            for d in data:
                task = SendTask.from_dict(d)
                self.tasks.append(task)
                self._add_row(task)


# ─────────────────────────────────────────────────────────
#  SIDE PANEL
# ─────────────────────────────────────────────────────────
class SidePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(280)
        self.setMaximumWidth(360)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Parser hits
        hdr1 = QWidget(); hdr1.setStyleSheet(f"background:{C['bg1']}; border-bottom:1px solid {C['border']};")
        h1l  = QHBoxLayout(hdr1); h1l.setContentsMargins(10, 6, 10, 6)
        h1l.addWidget(make_label("PARSER HITS", "heading"))
        layout.addWidget(hdr1)

        self.parser_table = QTableWidget(0, 2)
        self.parser_table.setHorizontalHeaderLabels(["Name", "Count"])
        self.parser_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.parser_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.parser_table.setColumnWidth(1, 60)
        self.parser_table.verticalHeader().setVisible(False)
        self.parser_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.parser_table.setMaximumHeight(220)
        layout.addWidget(self.parser_table)

        layout.addWidget(h_sep())

        # Last packet
        hdr2 = QWidget(); hdr2.setStyleSheet(f"background:{C['bg1']}; border-bottom:1px solid {C['border']};")
        h2l  = QHBoxLayout(hdr2); h2l.setContentsMargins(10, 6, 10, 6)
        h2l.addWidget(make_label("LETZTES PAKET", "heading"))
        layout.addWidget(hdr2)

        self.last_pkt_widget = QWidget()
        self.last_pkt_widget.setStyleSheet(f"background: {C['bg0']};")
        lpk_l = QVBoxLayout(self.last_pkt_widget)
        lpk_l.setContentsMargins(12, 10, 12, 10)
        lpk_l.setSpacing(4)
        self.lp_id  = QLabel("–")
        self.lp_id.setStyleSheet(f"color: {C['accent']}; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        self.lp_ts  = QLabel("")
        self.lp_ts.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent; border: none;")
        self.lp_raw = QLabel("")
        self.lp_raw.setStyleSheet(f"color: {C['text']}; font-size: 12px; background: transparent; border: none;")
        self.lp_raw.setWordWrap(True)
        self.lp_parsed = QLabel("")
        self.lp_parsed.setStyleSheet(f"color: {C['accent2']}; font-size: 11px; background: transparent; border: none;")
        self.lp_parsed.setWordWrap(True)
        lpk_l.addWidget(self.lp_id)
        lpk_l.addWidget(self.lp_ts)
        lpk_l.addWidget(self.lp_raw)
        lpk_l.addWidget(self.lp_parsed)
        lpk_l.addStretch()
        layout.addWidget(self.last_pkt_widget)
        layout.addStretch()

        self._hit_map = {}

    def update_hit(self, name: str):
        self._hit_map[name] = self._hit_map.get(name, 0) + 1
        # Refresh table
        self.parser_table.setRowCount(0)
        for n, c in sorted(self._hit_map.items(), key=lambda x: -x[1]):
            row = self.parser_table.rowCount()
            self.parser_table.insertRow(row)
            self.parser_table.setRowHeight(row, 24)
            ni = QTableWidgetItem(n); ni.setForeground(QColor(C["accent4"]))
            ci = QTableWidgetItem(str(c)); ci.setForeground(QColor(C["accent"])); ci.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.parser_table.setItem(row, 0, ni)
            self.parser_table.setItem(row, 1, ci)

    def update_last(self, msg: can.Message, parsed_name: str, parsed_data: dict):
        id_str = f"{'0x%08X' % msg.arbitration_id if msg.is_extended_id else '0x%03X' % msg.arbitration_id}"
        ts     = datetime.fromtimestamp(msg.timestamp).strftime("%H:%M:%S.%f")[:12]
        raw    = " ".join(f"{b:02X}" for b in msg.data)
        self.lp_id.setText(id_str)
        self.lp_ts.setText(f"{ts}  ·  DLC {msg.dlc}  ·  {'EXT' if msg.is_extended_id else 'STD'}")
        self.lp_raw.setText(raw)
        if parsed_name:
            parts = [f"{k}: {v} {u}".strip() for k, (v, u) in parsed_data.items()]
            self.lp_parsed.setText(f"[{parsed_name}]\n" + "\n".join(parts))
        else:
            self.lp_parsed.setText("")




# ─────────────────────────────────────────────────────────
#  PARSER EDITOR TAB
# ─────────────────────────────────────────────────────────
class FieldDialog(QDialog):
    """Edit a single field definition."""
    def __init__(self, field: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Feld bearbeiten")
        self.setMinimumWidth(380)
        self._build()
        if field:
            self._load(field)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        form = QFormLayout(); form.setSpacing(8)

        self.e_name   = QLineEdit(); self.e_name.setPlaceholderText("z.B. Voltage")
        self.e_offset = QSpinBox();  self.e_offset.setRange(0, 63)
        self.e_type   = QComboBox(); self.e_type.addItems(FIELD_TYPES)
        self.e_scale  = QLineEdit("1.0")
        self.e_add    = QLineEdit("0.0")
        self.e_unit   = QLineEdit(); self.e_unit.setPlaceholderText("V, A, °C …")
        self.e_fmt    = QLineEdit(".2f"); self.e_fmt.setPlaceholderText(".2f  /  d  /  016b")

        form.addRow(make_label("Name:", "dim"),        self.e_name)
        form.addRow(make_label("Byte-Offset:", "dim"), self.e_offset)
        form.addRow(make_label("Typ:", "dim"),          self.e_type)
        form.addRow(make_label("Scale:", "dim"),        self.e_scale)
        form.addRow(make_label("Add:", "dim"),          self.e_add)
        form.addRow(make_label("Einheit:", "dim"),      self.e_unit)
        form.addRow(make_label("Format:", "dim"),       self.e_fmt)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load(self, f):
        self.e_name.setText(f.get("name", ""))
        self.e_offset.setValue(int(f.get("offset", 0)))
        idx = FIELD_TYPES.index(f.get("type", "u8")) if f.get("type","u8") in FIELD_TYPES else 0
        self.e_type.setCurrentIndex(idx)
        self.e_scale.setText(str(f.get("scale", 1.0)))
        self.e_add.setText(str(f.get("add", 0.0)))
        self.e_unit.setText(f.get("unit", ""))
        self.e_fmt.setText(f.get("fmt", ".2f"))

    def get_field(self) -> dict:
        return {
            "name":   self.e_name.text().strip(),
            "offset": self.e_offset.value(),
            "type":   self.e_type.currentText(),
            "scale":  float(self.e_scale.text() or "1"),
            "add":    float(self.e_add.text() or "0"),
            "unit":   self.e_unit.text().strip(),
            "fmt":    self.e_fmt.text().strip() or "g",
        }


class ParserDialog(QDialog):
    """Edit one complete parser definition."""
    def __init__(self, pdef: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parser bearbeiten")
        self.setMinimumWidth(620)
        self.setMinimumHeight(500)
        self._fields = []
        self._build()
        if pdef:
            self._load(pdef)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        form = QFormLayout(); form.setSpacing(8)
        self.e_name    = QLineEdit(); self.e_name.setPlaceholderText("Parser Name")
        self.e_can_id  = QLineEdit(); self.e_can_id.setPlaceholderText("0x2900")
        self.e_mask    = QLineEdit("0xFFFFFFFF"); self.e_mask.setPlaceholderText("0xFFFFFFFF")
        form.addRow(make_label("Name:", "dim"),    self.e_name)
        form.addRow(make_label("CAN-ID:", "dim"),  self.e_can_id)
        form.addRow(make_label("Maske:", "dim"),   self.e_mask)
        layout.addLayout(form)

        # Multiplex section
        mux_grp = QFrame()
        mux_grp.setStyleSheet(f"background: {C['bg2']}; border: 1px solid {C['border']};")
        mux_l = QVBoxLayout(mux_grp); mux_l.setContentsMargins(10,8,10,8); mux_l.setSpacing(6)
        mux_hdr = QHBoxLayout()
        self.chk_mux = QCheckBox("Multiplexing aktivieren")
        self.chk_mux.setStyleSheet(f"background: transparent; border: none;")
        self.chk_mux.toggled.connect(self._on_mux_toggle)
        mux_hdr.addWidget(self.chk_mux); mux_hdr.addStretch()
        mux_l.addLayout(mux_hdr)

        mux_form = QFormLayout(); mux_form.setSpacing(6)
        self.e_mux_byte  = QSpinBox();  self.e_mux_byte.setRange(0, 7)
        self.e_mux_val   = QLineEdit("0"); self.e_mux_val.setPlaceholderText("0")
        self.e_mux_mask  = QLineEdit("0xFF"); self.e_mux_mask.setPlaceholderText("0xFF")
        self._mux_byte_lbl  = make_label("Mux Byte:", "dim")
        self._mux_val_lbl   = make_label("Mux Wert:", "dim")
        self._mux_mask_lbl  = make_label("Mux Maske:", "dim")
        mux_form.addRow(self._mux_byte_lbl, self.e_mux_byte)
        mux_form.addRow(self._mux_val_lbl,  self.e_mux_val)
        mux_form.addRow(self._mux_mask_lbl, self.e_mux_mask)
        mux_l.addLayout(mux_form)
        self._mux_widgets = [self._mux_byte_lbl, self.e_mux_byte,
                             self._mux_val_lbl, self.e_mux_val,
                             self._mux_mask_lbl, self.e_mux_mask]
        self._on_mux_toggle(False)
        layout.addWidget(mux_grp)

        layout.addWidget(h_sep())

        # Fields
        fhdr = QHBoxLayout()
        fhdr.addWidget(make_label("FELDER", "heading"))
        fhdr.addStretch()
        add_f = make_btn("+ Feld", "success"); add_f.clicked.connect(self._add_field)
        fhdr.addWidget(add_f)
        layout.addLayout(fhdr)

        self.field_table = QTableWidget(0, 7)
        self.field_table.setHorizontalHeaderLabels(["Name","Offset","Typ","Scale","Add","Einheit",""])
        self.field_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, w in [(1,55),(2,70),(3,65),(4,55),(5,60),(6,34)]:
            self.field_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.field_table.setColumnWidth(col, w)
        self.field_table.verticalHeader().setVisible(False)
        self.field_table.setMinimumHeight(160)
        self.field_table.cellDoubleClicked.connect(self._edit_field)
        layout.addWidget(self.field_table)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Speichern")
        btns.accepted.connect(self._accept); btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_mux_toggle(self, checked):
        for w in self._mux_widgets:
            w.setVisible(checked)

    def _load(self, p):
        self.e_name.setText(p.get("name",""))
        self.e_can_id.setText(p.get("can_id","0x0000"))
        self.e_mask.setText(p.get("can_mask","0xFFFFFFFF"))
        has_mux = "mux_byte" in p
        self.chk_mux.setChecked(has_mux)
        if has_mux:
            self.e_mux_byte.setValue(int(p.get("mux_byte",0)))
            self.e_mux_val.setText(str(p.get("mux_value",0)))
            self.e_mux_mask.setText(p.get("mux_mask","0xFF"))
        self._fields = copy.deepcopy(p.get("fields",[]))
        self._refresh_fields()

    def _add_field(self):
        dlg = FieldDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._fields.append(dlg.get_field())
            self._refresh_fields()

    def _edit_field(self, row, _col):
        if row < len(self._fields):
            dlg = FieldDialog(field=self._fields[row], parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._fields[row] = dlg.get_field()
                self._refresh_fields()

    def _refresh_fields(self):
        self.field_table.setRowCount(0)
        for f in self._fields:
            r = self.field_table.rowCount()
            self.field_table.insertRow(r)
            self.field_table.setRowHeight(r, 24)
            vals = [f.get("name",""), str(f.get("offset",0)), f.get("type","u8"),
                    str(f.get("scale",1)), str(f.get("add",0)), f.get("unit","")]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setForeground(QColor(C["text"]))
                self.field_table.setItem(r, c, it)
            del_btn = make_btn("✕","danger"); del_btn.setFixedSize(30,22)
            idx = r
            del_btn.clicked.connect(lambda _, i=idx: self._del_field(i))
            self.field_table.setCellWidget(r, 6, del_btn)

    def _del_field(self, idx):
        if idx < len(self._fields):
            self._fields.pop(idx)
            self._refresh_fields()

    def _accept(self):
        if not self.e_name.text().strip():
            QMessageBox.warning(self,"Fehler","Name darf nicht leer sein."); return
        try: int(self.e_can_id.text().strip(), 16)
        except: QMessageBox.warning(self,"Fehler","Ungültige CAN-ID."); return
        self.accept()

    def get_parser(self) -> dict:
        p = {
            "name":     self.e_name.text().strip(),
            "can_id":   self.e_can_id.text().strip(),
            "can_mask": self.e_mask.text().strip(),
            "fields":   copy.deepcopy(self._fields),
        }
        if self.chk_mux.isChecked():
            p["mux_byte"]  = self.e_mux_byte.value()
            p["mux_value"] = int(self.e_mux_val.text().strip() or "0", 0)
            p["mux_mask"]  = self.e_mux_mask.text().strip()
        return p


class ParserTab(QWidget):
    """Manage the ACTIVE_PARSERS list with a GUI."""

    def __init__(self):
        super().__init__()
        self._build()
        self._refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        bar = QWidget(); bar.setStyleSheet(f"background:{C['bg1']}; border-bottom:1px solid {C['border']};")
        bl  = QHBoxLayout(bar); bl.setContentsMargins(8,4,8,4); bl.setSpacing(6)
        btn_new    = make_btn("+ Neuer Parser", "primary"); btn_new.clicked.connect(self._new)
        btn_dup    = make_btn("Duplizieren");               btn_dup.clicked.connect(self._duplicate)
        btn_del    = make_btn("Löschen","danger");          btn_del.clicked.connect(self._delete)
        btn_reset  = make_btn("Built-ins wiederherstellen"); btn_reset.clicked.connect(self._reset)
        btn_export = make_btn("Export JSON");                btn_export.clicked.connect(self._export)
        btn_import = make_btn("Import JSON");                btn_import.clicked.connect(self._import)
        bl.addWidget(btn_new); bl.addWidget(btn_dup); bl.addWidget(btn_del)
        bl.addStretch()
        bl.addWidget(btn_reset); bl.addWidget(btn_export); bl.addWidget(btn_import)
        layout.addWidget(bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name","CAN-ID","Maske","Mux","Felder"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, w in [(1,115),(2,115),(3,90),(4,55)]:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self._edit)
        layout.addWidget(self.table)

        # JSON preview at the bottom
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C['border']};"); layout.addWidget(sep)

        hint = make_label("Doppelklick zum Bearbeiten  ·  JSON-Format kompatibel mit Export/Import", "dim")
        hint.setContentsMargins(10,4,10,4)
        layout.addWidget(hint)

    def _refresh(self):
        self.table.setRowCount(0)
        for p in ACTIVE_PARSERS:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, 24)
            mux = f"byte[{p['mux_byte']}]=={p.get('mux_value',0)}" if "mux_byte" in p else "–"
            vals = [p.get("name",""), p.get("can_id",""), p.get("can_mask","0xFFFFFFFF"),
                    mux, str(len(p.get("fields",[])))]
            colors = [C["text_br"], C["accent"], C["text_dim"], C["accent4"], C["text_dim"]]
            for c,(v,col) in enumerate(zip(vals,colors)):
                it = QTableWidgetItem(v); it.setForeground(QColor(col))
                self.table.setItem(r, c, it)

    def _selected_row(self):
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def _new(self):
        dlg = ParserDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ACTIVE_PARSERS.append(dlg.get_parser())
            self._refresh()

    def _edit(self, row=None, _col=None):
        if row is None: row = self._selected_row()
        if row < 0 or row >= len(ACTIVE_PARSERS): return
        dlg = ParserDialog(pdef=ACTIVE_PARSERS[row], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ACTIVE_PARSERS[row] = dlg.get_parser()
            self._refresh()

    def _duplicate(self):
        row = self._selected_row()
        if row < 0: return
        new_p = copy.deepcopy(ACTIVE_PARSERS[row])
        new_p["name"] += " (Kopie)"
        ACTIVE_PARSERS.insert(row+1, new_p)
        self._refresh()

    def _delete(self):
        row = self._selected_row()
        if row < 0: return
        name = ACTIVE_PARSERS[row].get("name","?")
        if QMessageBox.question(self,"Löschen",f'Parser "{name}" wirklich löschen?',
                                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            ACTIVE_PARSERS.pop(row)
            self._refresh()

    def _reset(self):
        if QMessageBox.question(self,"Built-ins","Alle Parser durch die eingebauten Defaults ersetzen?",
                                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            ACTIVE_PARSERS.clear()
            ACTIVE_PARSERS.extend(copy.deepcopy(BUILTIN_PARSERS))
            self._refresh()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self,"Parser exportieren","parsers.json","JSON (*.json)")
        if path:
            with open(path,"w") as f:
                json.dump(ACTIVE_PARSERS, f, indent=2)

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self,"Parser importieren","","JSON (*.json)")
        if path:
            with open(path) as f:
                data = json.load(f)
            ACTIVE_PARSERS.clear()
            ACTIVE_PARSERS.extend(data)
            self._refresh()


# ─────────────────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAN // MON")
        self.resize(1400, 800)
        self._worker = CANWorker()
        self._rx_count = 0
        self._tx_count = 0
        self._err_count = 0
        self._rate_count = 0
        self._build()
        self._wire()

    def _build(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background:{C['bg1']}; border-bottom:1px solid {C['border']};")
        header.setFixedHeight(50)
        hl = QHBoxLayout(header); hl.setContentsMargins(14, 0, 14, 0); hl.setSpacing(16)

        logo = QLabel("CAN<span style='color:%s'>//</span>MON" % C["accent2"])
        logo.setTextFormat(Qt.TextFormat.RichText)
        logo.setStyleSheet(f"color:{C['accent']}; font-family:'Share Tech Mono','Consolas',monospace; font-size:15px; letter-spacing:3px;")

        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color:{C['danger']}; font-size:10px;")
        self.status_lbl = QLabel("Nicht verbunden")
        self.status_lbl.setStyleSheet(f"color:{C['text_dim']}; font-size:11px;")

        self.lbl_rx   = QLabel("RX <b>0</b>"); self.lbl_rx.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_tx   = QLabel("TX <b>0</b>"); self.lbl_tx.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_err  = QLabel("ERR <b>0</b>"); self.lbl_err.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_rate = QLabel("0 pkt/s")
        for l in [self.lbl_rx, self.lbl_tx, self.lbl_err, self.lbl_rate]:
            l.setStyleSheet(f"color:{C['text_dim']}; font-size:10px;")

        self.btn_connect    = make_btn("Verbinden", "primary")
        self.btn_disconnect = make_btn("Trennen")
        self.btn_disconnect.setEnabled(False)

        hl.addWidget(logo)
        hl.addWidget(self.dot)
        hl.addWidget(self.status_lbl)
        hl.addStretch()
        hl.addWidget(self.lbl_rx); hl.addWidget(self.lbl_tx)
        hl.addWidget(self.lbl_err); hl.addWidget(self.lbl_rate)
        hl.addWidget(v_sep())
        hl.addWidget(self.btn_connect)
        hl.addWidget(self.btn_disconnect)
        root.addWidget(header)

        # ── Body ────────────────────────────────────────
        body = QSplitter(Qt.Orientation.Horizontal)
        body.setHandleWidth(1)

        # Tabs
        self.tabs = QTabWidget()
        self.log_tab    = LogTab()
        self.live_tab   = LiveTab()
        self.send_tab   = SendTab()
        self.tasks_tab  = TasksTab()
        self.parser_tab = ParserTab()
        self.tabs.addTab(self.log_tab,    "Log")
        self.tabs.addTab(self.live_tab,   "Live View")
        self.tabs.addTab(self.send_tab,   "Senden")
        self.tabs.addTab(self.tasks_tab,  "Sendetasks")
        self.tabs.addTab(self.parser_tab, "Parser")
        body.addWidget(self.tabs)

        # Side panel
        self.side = SidePanel()
        self.side.setStyleSheet(f"background:{C['bg1']}; border-left:1px solid {C['border']};")
        body.addWidget(self.side)
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 1)

        root.addWidget(body)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Bereit.")

        # Rate timer
        self._rate_timer = QTimer()
        self._rate_timer.timeout.connect(self._update_rate)
        self._rate_timer.start(1000)

    def _wire(self):
        self.btn_connect.clicked.connect(self._connect)
        self.btn_disconnect.clicked.connect(self._disconnect)

        self._worker.frame_received.connect(self._on_frame)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.connected.connect(self._on_connected)
        self._worker.disconnected.connect(self._on_disconnected)

        self.send_tab.send_requested.connect(self._send_msg)
        self.tasks_tab.send_requested.connect(self._send_msg)

    def _connect(self):
        dlg = ConnectDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        iface, channel, bitrate, extra = dlg.get_params()
        self.status_lbl.setText(f"Verbinde ({iface} · {channel}) …")
        self.dot.setStyleSheet(f"color:{C['warn']}; font-size:10px;")
        self._worker.connect(iface, channel, bitrate, extra)

    def _disconnect(self):
        self._worker.disconnect()

    def _send_msg(self, msg: can.Message):
        if self._worker.send(msg):
            self._tx_count += 1
            self.lbl_tx.setText(f"TX <b>{self._tx_count}</b>")

    def _on_frame(self, msg: can.Message):
        self._rx_count += 1
        self._rate_count += 1
        self.lbl_rx.setText(f"RX <b>{self._rx_count}</b>")

        results = apply_parsers(ACTIVE_PARSERS, msg.arbitration_id, bytes(msg.data))

        if results:
            for pname, mux_key, fields in results:
                self.log_tab.append(msg, pname, mux_key, fields)
                self.live_tab.update(msg, pname, mux_key, fields)
                self.side.update_hit(pname)
            # Show first match in side panel
            self.side.update_last(msg, results[0][0], results[0][2])
        else:
            self.log_tab.append(msg, None, "", {})
            self.live_tab.update(msg, None, "", {})
            self.side.update_last(msg, None, {})

    def _on_error(self, msg: str):
        self._err_count += 1
        self.lbl_err.setText(f"ERR <b>{self._err_count}</b>")
        self.status_bar.showMessage(f"⚠ {msg}", 5000)

    def _on_connected(self):
        self.dot.setStyleSheet(f"color:{C['ok']}; font-size:10px;")
        self.status_lbl.setText("Verbunden")
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        self.status_bar.showMessage("Verbunden.")

    def _on_disconnected(self):
        self.dot.setStyleSheet(f"color:{C['danger']}; font-size:10px;")
        self.status_lbl.setText("Nicht verbunden")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.status_bar.showMessage("Getrennt.")

    def _update_rate(self):
        self.lbl_rate.setText(f"{self._rate_count} pkt/s")
        self._rate_count = 0

    def closeEvent(self, event):
        self.tasks_tab._stop_all()
        self._worker.disconnect()
        self._worker.wait(2000)
        super().closeEvent(event)


# ─────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CAN Monitor")
    app.setOrganizationName("CANMonitor")
    app.setStyleSheet(STYLESHEET)

    # Dark palette for native widgets
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(C["bg0"]))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(C["text"]))
    palette.setColor(QPalette.ColorRole.Base,            QColor(C["bg1"]))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(C["bg2"]))
    palette.setColor(QPalette.ColorRole.Text,            QColor(C["text"]))
    palette.setColor(QPalette.ColorRole.Button,          QColor(C["bg2"]))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(C["text"]))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(C["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(C["bg0"]))
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
