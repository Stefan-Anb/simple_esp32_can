#include <stdio.h>
#include <string.h>
#include <sys/param.h>
#include <sys/stat.h>
#include <unistd.h>
#include "driver/twai.h"
#include "driver/uart.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_spiffs.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "lwip/err.h"
#include "lwip/sockets.h"
#include "nvs.h"
#include "nvs_flash.h"

// --- KONFIGURATION ---
#define ENABLE_GPIO     35
#define TCP_PORT        8080
#define CAN_TX_IO       37
#define CAN_RX_IO       36

// --- UART LOG KONFIGURATION ---
#define UART_LOG_RX_PIN 7
#define UART_LOG_PORT   UART_NUM_1
#define UART_LOG_BAUD   115200
#define LOG_MAX_SIZE    (200 * 1024) // 200 KB pro Datei (max 400 KB gesamt durch Rotation)

static const char* TAG = "SLCAN_ESP32";
static bool is_driver_installed = false;
static bool is_bus_started = false;
static char station_ip[16] = "n/a";
static char ap_ssid_current[33] = "ESP32-Config";
static char sta_ssid_current[33] = "";

// --- HTML FÜR DIE WEB-KONFIGURATION ---
// Keep template CSS and structure in code but build page dynamically in the GET handler

// --- HTTP GET HANDLER (Zeigt die Seite an) ---
esp_err_t get_handler(httpd_req_t* req) {
    const char* head = "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>"
        "body{font-family:Arial,sans-serif;background-color:#f4f4f9;color:#333;display:flex;justify-content:center;margin-top:50px;}"
        "div.box{background:#fff;padding:30px;border-radius:8px;box-shadow:0 4px 8px rgba(0,0,0,0.1);width:340px;}"
        "h2{margin-top:0;text-align:center;}input[type='text']{width:100%;padding:10px;margin:10px 0 20px 0;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;}"
        "input[type='submit']{background:#007BFF;color:#fff;border:none;padding:12px;width:100%;border-radius:4px;cursor:pointer;font-size:16px;}"
        "input[type='submit']:hover{background:#0056b3;}a.log-btn{display:block;text-align:center;margin-top:15px;color:#007BFF;text-decoration:none;font-weight:bold;}"
        "</style></head><body><div class='box'><h2>WLAN Setup</h2>";

    const char* mid1 = "<p><strong>Station IP:</strong> ";
    const char* mid2 = "</p><form action=\"/save\" method=\"POST\">"
                       "<label>Access Point SSID:</label><input type=\"text\" name=\"ap_ssid\" value=\"";
    const char* mid3 = "\">"
                       "<label>External Wifi SSID:</label><input type=\"text\" name=\"ssid\">"
                       "<label>Passwort:</label><input type=\"text\" name=\"pass\">"
                       "<input type=\"submit\" value=\"Speichern & Neustart\">"
                       "</form><a href=\"/log\" class=\"log-btn\" target=\"_blank\">UART Log ansehen</a></div></body></html>";

    httpd_resp_send_chunk(req, head, strlen(head));
    httpd_resp_send_chunk(req, mid1, strlen(mid1));
    httpd_resp_send_chunk(req, station_ip, strlen(station_ip));
    httpd_resp_send_chunk(req, mid2, strlen(mid2));
    httpd_resp_send_chunk(req, ap_ssid_current, strlen(ap_ssid_current));
    httpd_resp_send_chunk(req, mid3, strlen(mid3));
    httpd_resp_send_chunk(req, NULL, 0);
    return ESP_OK;
}

// --- HTTP GET HANDLER (Zeigt das UART Log formatiert im Browser an) ---
// --- HTTP GET HANDLER (Zeigt das UART Log formatiert im Browser an) ---
esp_err_t log_handler(httpd_req_t *req) {
    // Setzen der UTF-8 Kodierung und HTML als Typ
    httpd_resp_set_type(req, "text/html; charset=utf-8");
    
    // HTML-Kopf inklusive JavaScript für die ANSI-zu-HTML Farbkonvertierung
    const char* html_head = 
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>UART Log</title>"
        "<style>"
        "body{background:#1e1e1e;color:#d4d4d4;padding:20px;font-family:monospace;}"
        ".btn{background:#dc3545;color:#fff;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;font-family:Arial;font-size:14px;margin-bottom:15px;}"
        ".btn:hover{background:#c82333;}"
        "</style>"
        "<script>"
        "window.onload = function() {"
        "  var p = document.getElementById('log-output');"
        // Sucht nach ANSI-Codes (Escape-Zeichen \x1B) und wandelt sie in spans um
        "  p.innerHTML = p.innerHTML.replace(/\\x1B\\[([0-9;]*)m/g, function(m, p1) {"
        "    if (p1 === '0' || p1 === '') return '</span>';" // Reset = Span schließen
        "    let s = '';"
        "    if (p1.includes('31')) s = 'color:#ff5555;'; "       // Error (Rot)
        "    else if (p1.includes('32')) s = 'color:#50fa7b;'; "  // Info (Grün)
        "    else if (p1.includes('33')) s = 'color:#f1fa8c;'; "  // Warn (Gelb)
        "    else if (p1.includes('34')) s = 'color:#bd93f9;'; "  // Blau
        "    else if (p1.includes('36')) s = 'color:#8be9fd;'; "  // Cyan
        "    if (p1.includes('1;')) s += 'font-weight:bold;';"    // Fettgedruckt
        "    return s ? '<span style=\"' + s + '\">' : '';"
        "  });"
        "};"
        "</script>"
        "</head><body>"
        "<form action=\"/clear_log\" method=\"POST\">"
        "<input type=\"submit\" class=\"btn\" value=\"Log löschen\">"
        "</form><pre id=\"log-output\">";
        
    httpd_resp_send_chunk(req, html_head, strlen(html_head));

    char buf[512];
    
    // Zuerst das alte Log senden (falls vorhanden)
    FILE* f_old = fopen("/spiffs/log_old.txt", "r");
    if (f_old) {
        size_t read_bytes;
        while ((read_bytes = fread(buf, 1, sizeof(buf), f_old)) > 0) {
            httpd_resp_send_chunk(req, buf, read_bytes);
        }
        fclose(f_old);
    }

    // Dann das aktuelle Log senden
    FILE* f = fopen("/spiffs/log.txt", "r");
    if (f) {
        size_t read_bytes;
        while ((read_bytes = fread(buf, 1, sizeof(buf), f)) > 0) {
            httpd_resp_send_chunk(req, buf, read_bytes);
        }
        fclose(f);
    }

    // HTML-Fuß senden
    const char* html_foot = "</pre></body></html>";
    httpd_resp_send_chunk(req, html_foot, strlen(html_foot));

    // Chunked Transfer beenden
    httpd_resp_send_chunk(req, NULL, 0);
    return ESP_OK;
}

// --- HTTP POST HANDLER (Löscht die Log-Dateien) ---
esp_err_t clear_log_handler(httpd_req_t* req) {
    unlink("/spiffs/log.txt");
    unlink("/spiffs/log_old.txt");

    ESP_LOGI(TAG, "Log-Dateien wurden gelöscht.");

    // Redirect zurück zur Log-Seite (die nun leer sein wird)
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "/log");
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

static int hex_to_int(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    return 0;
}

void url_decode(char* str) {
    char* data = str;
    while (*data) {
        if (*data == '+') {
            *str = ' ';
        } else if (*data == '%' && data[1] && data[2]) {
            *str = (char)((hex_to_int(data[1]) << 4) | hex_to_int(data[2]));
            data += 2;
        } else {
            *str = *data;
        }
        data++;
        str++;
    }
    *str = '\0';
}

// --- HTTP POST HANDLER (Speichert die Daten und startet neu) ---
esp_err_t post_handler(httpd_req_t* req) {
    char buf[100];
    int ret, remaining = req->content_len;

    if ((ret = httpd_req_recv(req, buf, MIN(remaining, sizeof(buf)))) <= 0) {
        return ESP_FAIL;
    }
    buf[ret] = '\0';

    char ssid[32] = {0};
    char pass[64] = {0};

    // Read fields if present (password may be empty)
    char ap_ssid[33] = {0};
    httpd_query_key_value(buf, "ap_ssid", ap_ssid, sizeof(ap_ssid));
    httpd_query_key_value(buf, "ssid", ssid, sizeof(ssid));
    httpd_query_key_value(buf, "pass", pass, sizeof(pass));

    url_decode(ap_ssid);
    url_decode(ssid);
    url_decode(pass);

    ESP_LOGI(TAG, "POST received: ap_ssid='%s', ssid='%s', pass_len=%d", ap_ssid, ssid, (int)strlen(pass));

    nvs_handle_t nvs;
    if (nvs_open("wifi_cfg", NVS_READWRITE, &nvs) == ESP_OK) {
        // Only update STA SSID/pass if a non-empty password was provided
        if (strlen(pass) > 0 && strlen(ssid) > 0) {
            nvs_set_str(nvs, "ssid", ssid);
            nvs_set_str(nvs, "pass", pass);
        } else {
            ESP_LOGI(TAG, "Empty password -> STA SSID/pass not updated");
        }

        if (strlen(ap_ssid) > 0) {
            nvs_set_str(nvs, "ap_ssid", ap_ssid);
        }
        nvs_commit(nvs);
        nvs_close(nvs);
    }

    httpd_resp_send(req, "Gespeichert! ESP32 startet neu...", HTTPD_RESP_USE_STRLEN);
    vTaskDelay(pdMS_TO_TICKS(1000));
    esp_restart();
    return ESP_OK;
}

// --- WEBSERVER STARTEN ---
httpd_handle_t start_webserver(void) {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    httpd_handle_t server = NULL;
    if (httpd_start(&server, &config) == ESP_OK) {
        httpd_uri_t uri_get = {.uri = "/", .method = HTTP_GET, .handler = get_handler, .user_ctx = NULL};
        httpd_uri_t uri_post = {.uri = "/save", .method = HTTP_POST, .handler = post_handler, .user_ctx = NULL};
        httpd_uri_t uri_log = {.uri = "/log", .method = HTTP_GET, .handler = log_handler, .user_ctx = NULL};
        httpd_uri_t uri_clear = {
            .uri = "/clear_log", .method = HTTP_POST, .handler = clear_log_handler, .user_ctx = NULL};

        httpd_register_uri_handler(server, &uri_get);
        httpd_register_uri_handler(server, &uri_post);
        httpd_register_uri_handler(server, &uri_log);
        httpd_register_uri_handler(server, &uri_clear);
    }
    return server;
}

// --- WIFI HANDLER ---
static void event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGI(TAG, "WiFi verloren, verbinde neu...");
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*)event_data;
        ESP_LOGI(TAG, "Verbunden! IP: " IPSTR, IP2STR(&event->ip_info.ip));
        // Store human-readable IP for web UI
        snprintf(station_ip, sizeof(station_ip), IPSTR, IP2STR(&event->ip_info.ip));
    }
}

void wifi_init_ap_sta(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    esp_netif_create_default_wifi_ap();
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &event_handler, NULL, NULL);
    esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &event_handler, NULL, NULL);

    // Read stored AP SSID and STA credentials from NVS (if present)
    wifi_config_t ap_config = {0};
    wifi_config_t sta_config = {0};
    nvs_handle_t nvs;
    esp_err_t err = nvs_open("wifi_cfg", NVS_READONLY, &nvs);
    if (err == ESP_OK) {
        size_t len = sizeof(ap_ssid_current);
        if (nvs_get_str(nvs, "ap_ssid", ap_ssid_current, &len) == ESP_OK) {
            ESP_LOGI(TAG, "Gespeicherte AP SSID: %s", ap_ssid_current);
        }

        len = sizeof(sta_config.sta.ssid);
        if (nvs_get_str(nvs, "ssid", (char*)sta_config.sta.ssid, &len) == ESP_OK) {
            strncpy(sta_ssid_current, (char*)sta_config.sta.ssid, sizeof(sta_ssid_current) - 1);
        }
        len = sizeof(sta_config.sta.password);
        nvs_get_str(nvs, "pass", (char*)sta_config.sta.password, &len);
        nvs_close(nvs);
        ESP_LOGI(TAG, "Gespeicherte STA SSID gefunden: %s", sta_config.sta.ssid);
    } else {
        ESP_LOGW(TAG, "Keine WLAN-Daten gespeichert. Starte nur im AP-Modus.");
    }

    // Apply AP config using the potentially-updated ap_ssid_current
    strncpy((char*)ap_config.ap.ssid, ap_ssid_current, sizeof(ap_config.ap.ssid) - 1);
    ap_config.ap.ssid_len = strlen(ap_ssid_current);
    ap_config.ap.channel = 1;
    ap_config.ap.password[0] = '\0';
    ap_config.ap.max_connection = 4;
    ap_config.ap.authmode = WIFI_AUTH_OPEN;

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
    if (strlen((char*)sta_config.sta.ssid) > 0) {
        ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta_config));
    }

    ESP_ERROR_CHECK(esp_wifi_start());
    start_webserver();
}

// --- SLCAN LOGIK ---
esp_err_t setup_twai(int speed_idx) {
    if (is_driver_installed) {
        twai_driver_uninstall();
        is_driver_installed = false;
    }
    ESP_LOGI(TAG, "Setup port with speed index %d", speed_idx);
    twai_general_config_t g_cfg = TWAI_GENERAL_CONFIG_DEFAULT(CAN_TX_IO, CAN_RX_IO, TWAI_MODE_NORMAL);
    g_cfg.rx_queue_len = 200;
    g_cfg.tx_queue_len = 20;
    twai_filter_config_t f_cfg = TWAI_FILTER_CONFIG_ACCEPT_ALL();
    twai_timing_config_t t_cfg;

    switch (speed_idx) {
        case 0: t_cfg = (twai_timing_config_t)TWAI_TIMING_CONFIG_10KBITS(); break;
        case 4: t_cfg = (twai_timing_config_t)TWAI_TIMING_CONFIG_125KBITS(); break;
        case 6: t_cfg = (twai_timing_config_t)TWAI_TIMING_CONFIG_500KBITS(); break;
        case 8: t_cfg = (twai_timing_config_t)TWAI_TIMING_CONFIG_1MBITS(); break;
        default: t_cfg = (twai_timing_config_t)TWAI_TIMING_CONFIG_500KBITS(); break;
    }
    esp_err_t res = twai_driver_install(&g_cfg, &t_cfg, &f_cfg);
    if (res == ESP_OK) {
        is_driver_installed = true;
    }
    return res;
}

void slcan_task(void* pv) {
    struct sockaddr_in addr = {
        .sin_addr.s_addr = htonl(INADDR_ANY), .sin_family = AF_INET, .sin_port = htons(TCP_PORT)};
    int listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
    if (listen_sock < 0) {
        ESP_LOGE(TAG, "Socket erstellen fehlgeschlagen: errno %d", errno);
        vTaskDelete(NULL);
    }

    int opt = 1;
    setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    int err = bind(listen_sock, (struct sockaddr*)&addr, sizeof(addr));
    if (err != 0) {
        ESP_LOGE(TAG, "Socket bind fehlgeschlagen: errno %d", errno);
        close(listen_sock);
        vTaskDelete(NULL);
    }

    err = listen(listen_sock, 1);
    if (err != 0) {
        ESP_LOGE(TAG, "Socket listen fehlgeschlagen: errno %d", errno);
        close(listen_sock);
        vTaskDelete(NULL);
    }
    ESP_LOGI(TAG, "Server wartet auf Port %d...", TCP_PORT);

    char rx_buf[128];
    while (1) {
        int sock = accept(listen_sock, NULL, NULL);
        if (sock < 0) {
            vTaskDelay(pdMS_TO_TICKS(500));
            continue;
        }
        fcntl(sock, F_SETFL, O_NONBLOCK);
        ESP_LOGI(TAG, "PC verbunden!");

        int rx_idx = 0;
        while (1) {
            char c;
            if (recv(sock, &c, 1, 0) > 128) {
                if (errno != EAGAIN) {
                    break;
                }
            } else if (c == '\r') {
                rx_buf[rx_idx] = '\0';
                if (rx_buf[0] == 'S') {
                    setup_twai(rx_buf[1] - '0');
                    send(sock, "\r", 1, 0);
                } else if (rx_buf[0] == 'O') {
                    if (is_driver_installed && twai_start() == ESP_OK) {
                        is_bus_started = true;
                    }
                    send(sock, "\r", 1, 0);
                } else if (rx_buf[0] == 'C') {
                    if (is_bus_started) {
                        twai_stop();
                    }
                    is_bus_started = false;
                    send(sock, "\r", 1, 0);
                } else if ((rx_buf[0] == 't' || rx_buf[0] == 'T') && is_bus_started) {
                    twai_message_t msg = {.extd = (rx_buf[0] == 'T'),
                                          .data_length_code = hex_to_int(rx_buf[rx_buf[0] == 'T' ? 9 : 4])};
                    uint32_t id = 0;
                    int id_len = msg.extd ? 8 : 3;
                    for (int i = 0; i < id_len; i++) {
                        id = (id << 4) | hex_to_int(rx_buf[1 + i]);
                    }
                    msg.identifier = id;
                    for (int i = 0; i < msg.data_length_code; i++) {
                        msg.data[i] = (hex_to_int(rx_buf[id_len + 2 + (i * 2)]) << 4)
                                      | hex_to_int(rx_buf[id_len + 3 + (i * 2)]);
                    }
                    twai_transmit(&msg, 0);
                    send(sock, "\r", 1, 0);
                } else if (rx_buf[0] == 'V') {
                    send(sock, "V1013\r", 6, 0);
                }
                rx_idx = 0;
            } else if (rx_idx < 127) {
                rx_buf[rx_idx++] = c;
            }

            twai_message_t rmsg;
            if (is_bus_started && twai_receive(&rmsg, 0) == ESP_OK) {
                char out[64];
                int p = sprintf(out, rmsg.extd ? "T%08lX%d" : "t%03lX%d", (unsigned long)rmsg.identifier,
                                rmsg.data_length_code);
                for (int i = 0; i < rmsg.data_length_code; i++) {
                    p += sprintf(out + p, "%02X", rmsg.data[i]);
                }
                sprintf(out + p, "\r");
                send(sock, out, strlen(out), 0);
            }
            vTaskDelay(1);
        }
        if (is_bus_started) {
            twai_stop();
        }
        is_bus_started = false;
        close(sock);
        ESP_LOGI(TAG, "PC getrennt.");
    }
}

// --- UART LOGGER TASK ---
void uart_logger_task(void* pvParameters) {
    uart_config_t uart_config = {.baud_rate = UART_LOG_BAUD,
                                 .data_bits = UART_DATA_8_BITS,
                                 .parity = UART_PARITY_DISABLE,
                                 .stop_bits = UART_STOP_BITS_1,
                                 .flow_ctrl = UART_HW_FLOWCTRL_DISABLE};
    uart_param_config(UART_LOG_PORT, &uart_config);
    uart_set_pin(UART_LOG_PORT, UART_PIN_NO_CHANGE, UART_LOG_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(UART_LOG_PORT, 2048, 0, 0, NULL, 0);

    uint8_t data[256];

    while (1) {
        int length = uart_read_bytes(UART_LOG_PORT, data, sizeof(data) - 1, 100 / portTICK_PERIOD_MS);
        if (length > 0) {
            FILE* f = fopen("/spiffs/log.txt", "a");
            if (f) {
                fwrite(data, 1, length, f);
                fclose(f);
            }

            // Datei-Rotation bei Überschreiten der Maximalgröße
            struct stat st;
            if (stat("/spiffs/log.txt", &st) == 0 && st.st_size > LOG_MAX_SIZE) {
                ESP_LOGI(TAG, "Log rotiert.");
                unlink("/spiffs/log_old.txt");                    // Altes Log löschen
                rename("/spiffs/log.txt", "/spiffs/log_old.txt"); // Aktuelles Log wird zum alten Log
            }
        }
    }
}

// --- MAIN ---
void app_main(void) {
    // GPIO Init
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << ENABLE_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);
    gpio_set_level(ENABLE_GPIO, 1);

    // NVS Init
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // SPIFFS Init
    esp_vfs_spiffs_conf_t spiffs_conf = {
        .base_path = "/spiffs", .partition_label = NULL, .max_files = 3, .format_if_mount_failed = true};
    ret = esp_vfs_spiffs_register(&spiffs_conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Fehler beim Initialisieren von SPIFFS (%s)", esp_err_to_name(ret));
    }

    // WiFi & Webserver
    wifi_init_ap_sta();

    // Tasks starten
    xTaskCreate(slcan_task, "slcan", 4096, NULL, 5, NULL);
    xTaskCreate(uart_logger_task, "uart_log", 4096, NULL, 4, NULL);
}