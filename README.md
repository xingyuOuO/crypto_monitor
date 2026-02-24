# ⚡ Crypto 異常漲跌監測
> **資訊工程背景開發：結合信號處理邏輯的全市場即時監控終端**

## 📖 專案簡介
本專案將使用**信號濾波 (Signal Filtering)** 與 **異常檢測 (Anomaly Detection)** 的邏輯應用於加密貨幣市場。透過 `ccxt` 非同步技術，即時監控幣安合約市場中具備「爆發動能」與「主力資金流入」的標的。

---

## 🔬 核心監控邏輯 (Algorithm)
- **趨勢濾波**：15m EMA (7, 25, 99) 三線判定多空方向。
- **動能捕捉**：5m 週期內累積漲跌幅達 **5%** 即時觸發(短時間內的異常漲跌)。
- **成交量爆發**：偵測 **5 倍** 以上的異常放量（相較於 1h 均值）。
- **籌碼成本**：即時同步 Funding Rate，輔助判斷市場過熱度。

---

## 🖥 介面預覽 (Dashboard)
![Dashboard Screenshot](https://github.com/xingyuOuO/crypto_monitor/blob/main/%E8%9E%A2%E5%B9%95%E6%93%B7%E5%8F%96%E7%95%AB%E9%9D%A2%202026-02-24%20210740.png)


## 📂 專案架構 (Project Structure)
本專案採用邏輯與介面分離的架構開發，確保代碼的可維護性與清晰度：


```yaml
crypto_s1/
├── main_gui.py        # [前端] 客製化介面與互動邏輯，負責處理 UI 渲染
├── monitor_logic.py   # [後端] Binance API 通訊與計算核心，包含策略邏輯
├── requirements.txt   # [設定] 必要套件清單：列出 ccxt, pandas 等依賴
├── .gitignore         # [系統] 版本控制排除檔：自動忽略環境與暫存雜訊
└── README.md          # [文件] 專案說明書：記載開發動機與操作步驟

## ⚙️ 環境建置 (Setup)
1. **建立環境**：`python -m venv env`
2. **啟動環境**：`env\Scripts\activate` (Windows)
3. **安裝套件**：`pip install -r requirements.txt`
4. **啟動程式**：`python main_gui.py`

---
**Disclaimer**: 本專案僅供學術研究，投資有風險，使用前請謹慎評估。
