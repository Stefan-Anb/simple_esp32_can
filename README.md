# ESP32 SLCAN-TCP Bridge

Dieses Projekt verwandelt einen ESP32 in eine transparente Bridge zwischen einem **CAN-Bus** und einem **TCP-Socket**. Es implementiert das weit verbreitete **SLCAN (LAWICEL)** Protokoll, wodurch es nativ mit Bibliotheken wie `python-can` kompatibel ist.

## Features
* **WiFi Connectivity**: Verbindet sich als Station mit einem vorhandenen WLAN.
* **SLCAN Protokoll**: Unterstützt Standard (`t`) und Extended (`T`) Frames sowie Steuerbefehle (`O`, `C`, `S`, `V`).
* **Dynamische Bitrate**: Die CAN-Geschwindigkeit kann zur Laufzeit über das SLCAN-Interface konfiguriert werden.
* **TCP Server**: Lauscht standardmäßig auf Port `23`.
* **Robustheit**: Automatischer WiFi-Reconnect und sicheres Abschalten des CAN-Treibers bei Verbindungsabbruch.

## Hardware-Voraussetzungen
1. **ESP32 Modul** (ESP32, ESP32-S3, ESP32-C3 etc.)
2. **CAN-Transceiver** (z.B. SN65HVD230, MCP2551 oder TJA1050)
3. **Terminierung**: Achte auf den 120-Ohm-Abschlusswiderstand an deinem CAN-Bus.

### Verkabelung (Standard im Code)
| ESP32 Pin | Transceiver Pin | Beschreibung |
| :--- | :--- | :--- |
| GPIO 5 | TXD | CAN Transmit |
| GPIO 4 | RXD | CAN Receive |
| 3.3V / 5V | VCC | Spannungsversorgung |
| GND | GND | Masse |

---

## Software-Konfiguration

### 1. ESP-IDF Setup
Das Projekt wurde für **ESP-IDF v5.x** entwickelt. 
Stelle sicher, dass deine Umgebung korrekt geladen ist (`export.sh` oder über die IDE).

### 2. Anpassungen in `main.c`
Öffne die `main.c` und passe die folgenden Definitionen an:
```c
#define WIFI_SSID       "DEINE_SSID"
#define WIFI_PASS       "DEIN_PASSWORT"
#define CAN_TX_IO       GPIO_NUM_5
#define CAN_RX_IO       GPIO_NUM_4
```

### 3. Kompilieren und Flashen
```bash
idf.py set-target esp32  # oder dein jeweiliges Modell
idf.py build
idf.py flash monitor
```
Notiere dir die **IP-Adresse**, die im Monitor nach dem Verbindungsaufbau ausgegeben wird.

---

## Verwendung mit Python

Installiere zunächst `python-can`:
```bash
pip install python-can
```

Verwende das folgende Snippet, um eine Verbindung herzustellen:

```python
import can

def start_can():
    bus = can.interface.Bus(
        interface='slcan',
        channel='socket://192.168.1.50:23', # Ersetze mit deiner ESP-IP
        bitrate=500000
    )

    # Beispiel: Nachricht senden
    msg = can.Message(arbitration_id=0x123, data=[1, 2, 3, 4, 5, 6, 7, 8], is_extended_id=False)
    bus.send(msg)

    # Nachrichten empfangen
    for message in bus:
        print(f"Empfangen: {message}")

if __name__ == "__main__":
    start_can()
```

---

## Implementierte SLCAN Befehle
| Befehl | Beschreibung | Beispiel |
| :--- | :--- | :--- |
| `Sx` | Setze Bitrate (x=0..8) | `S6` (500k) |
| `O` | Open: Startet den CAN-Bus | `O` |
| `C` | Close: Stoppt den CAN-Bus | `C` |
| `t...` | Sende Standard Frame | `t12381122334455667788` |
| `T...` | Sende Extended Frame | `T0000012381122334455667788` |
| `V` | Version abfragen | Antwort: `V1013` |

---

## CAN-Monitor

Der CAN-Adapter kann mit jeder slcan-fähiger Software verwendet werden. Als Demonstration ist ein kleines CAN-Analysetool enthalten mit folgenden Features:

- Single Python File
- Konfigurierbare Parser für Pakete (ähnlich dbc-files, nur flexibler und einfacher einzustellen), um Strukturen in CAN-Messages zu dekodieren
    * Die Parser können auch Informationen aus der Message-ID extrahieren (wenn z.B. eine Node-Adresse in der Message ID codiert wird)
    * Multiplexing über ein Datenbyte in der CAN-Message
- Log View (Liste der empfangenen Pakete + Interpretation durch die Parser)
- Live View (eine Art Dashboard-Ansicht der geparsten Messages)
- Messages senden
- Sende-Tasks: Konfigurierbare Tasks um vorkonfigurierte Messages in einem festen Zeitraster zu senden
- Empfangszähler

## Lizenz
Apache 2.0