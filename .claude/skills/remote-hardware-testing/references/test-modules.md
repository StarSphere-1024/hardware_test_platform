# RK3576 测试模块清单

## 新开发模块（14）

| 模块 | Case 文件 | Function 目录 |
|---|---|---|
| HDMI | `cases/hdmi_case.json` | `functions/hdmi/` |
| SSD | `cases/ssd_case.json` | `functions/ssd/` |
| GPIO | `cases/gpio_case.json` | `functions/gpio/` |
| BLE | `cases/ble_case.json` | `functions/ble/` |
| 4G | `cases/4g_case.json` | `functions/4g/` |
| LoRa | `cases/lora_case.json` | `functions/lora/` |
| WiFi HALO | `cases/wifi_halo_case.json` | `functions/wifi_halo/` |
| Audio | `cases/audio_case.json` | `functions/audio/` |
| Fan | `cases/fan_case.json` | `functions/fan/` |
| EEPROM | `cases/eeprom_case.json` | `functions/eeprom/` |
| CSI | `cases/csi_case.json` | `functions/csi/` |
| DSI | `cases/dsi_case.json` | `functions/dsi/` |
| Hailo | `cases/hailo_case.json` | `functions/hailo/` |
| Maskrom | `cases/maskrom_case.json` | `functions/maskrom/` |

## 基础模块（6）

| 模块 | Case 文件 | Function 目录 |
|---|---|---|
| Ethernet | `cases/eth_case.json` | `functions/network/` |
| WiFi | `cases/wifi_case.json` | `functions/wifi/` |
| RTC | `cases/rtc_case.json` | `functions/rtc/` |
| I2C | `cases/i2c_case.json` | `functions/i2c/` |
| UART | `cases/uart_case.json` | `functions/uart/` |
| USB | `cases/usb_case.json` | `functions/usb/` |

## 推荐调试顺序

1. 先跑基础链路：`eth` → `wifi` → `uart` → `usb`。
2. 再跑总线相关：`i2c` → `rtc` → `eeprom` → `gpio`。
3. 最后跑外设和高负载模块：`audio`、`hdmi`、`csi`、`dsi`、`ssd`、`4g`、`lora`、`hailo`、`maskrom`。
