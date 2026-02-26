import asyncio
import pandas as pd
from datetime import datetime
import ccxt.async_support as ccxt

class CryptoMonitor:
    def __init__(self, ui_callback, status_callback):
        self.ui_callback = ui_callback
        self.status_callback = status_callback
        # 設置幣安期貨交易所實例
        self.exchange = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
        self.is_running = False

    async def check_symbol_logic(self, symbol, funding_rate):
        """
        核心策略判斷邏輯 (v3.5)：
        1. 數據抓取: 15m/5m K線 + Orderbook 深度
        2. 技術指標: EMA, Vol Ratio, OBI (Orderbook Imbalance)
        3. 加權強度評分 (0-100pt): 價格(35%), 成交量(30%), 深度(20%), 趨勢(15%)
        """
        try:
            display_name = symbol.split(':')[0].replace('/USDT', '')

            # --- 1. 並發抓取數據 (K線 + 深度) ---
            tasks = [
                self.exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100),
                self.exchange.fetch_ohlcv(symbol, timeframe='5m', limit=13),
                self.exchange.fetch_order_book(symbol, limit=20) # 抓取買賣牆深度
            ]
            results = await asyncio.gather(*tasks)

            # --- 2. EMA 趨勢判定 (15分鐘週期) ---
            df15 = pd.DataFrame(results[0], columns=['ts','o','h','l','c','v'])
            curr_p = df15['c'].iloc[-1]
            e7, e25, e99 = [df15['c'].ewm(span=s, adjust=False).mean().iloc[-1] for s in [7, 25, 99]]

            trend = "⚪"
            if curr_p > e7 and curr_p > e25 and curr_p > e99: trend = "🟢↑"
            elif curr_p < e7 and curr_p < e25 and curr_p < e99: trend = "🔴↓"

            # --- 3. 成交量與漲跌幅計算 (5分鐘週期) ---
            df5 = pd.DataFrame(results[1], columns=['ts','o','h','l','c','v'])
            avg_v = df5['v'].iloc[-13:-1].mean()
            curr_v = df5['v'].iloc[-2] 
            vol_ratio = curr_v / avg_v if avg_v > 0 else 0

            last3 = df5.iloc[-4:-1].copy()
            total_c = ((last3['c'].iloc[-1] - last3['o'].iloc[0]) / last3['o'].iloc[0]) * 100
            max_c = last3['c'].max()
            min_c = last3['c'].min()
            # 單根 K 線漲跌幅判定
            last_chg = ((last3['c'].iloc[-1] - last3['o'].iloc[-1]) / last3['o'].iloc[-1]) * 100

            # --- 4. Orderbook OBI 計算 ---
            ob = results[2]
            bid_vol = sum([v for p, v in ob['bids'][:5]]) # 前五檔買單總量
            ask_vol = sum([v for p, v in ob['asks'][:5]]) # 前五檔賣單總量
            # OBI 範圍在 -1 到 1 之間
            obi = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0

            # --- 5. 強度指標評分 (總分 100) ---
            strength_score = 0
            
            # (A) 價格動能 (佔 35分) - 10% 漲跌幅為滿分
            strength_score += min(35, (abs(total_c) / 10.0) * 35)
            
            # (B) 成交量評分 (佔 30分) - 10倍爆量為滿分
            strength_score += min(30, (vol_ratio / 10.0) * 30)
            
            # (C) OBI 深度評分 (佔 20分)
            if total_c > 0 and obi > 0.5:   strength_score += 20
            elif total_c > 0 and obi > 0.2: strength_score += 10
            elif total_c < 0 and obi < -0.5:  strength_score += 20
            elif total_c < 0 and obi < -0.2:  strength_score += 10
            
            # (D) 趨勢對齊評分 (佔 15分)
            is_trend_aligned = (total_c > 0 and trend == "🟢↑") or (total_c < 0 and trend == "🔴↓")
            if is_trend_aligned:
                strength_score += 15
            
            strength_score = int(strength_score) 

            # --- 6. 觸發條件判定 ---
            is_anomaly = abs(total_c) >= 5.0 or abs(last_chg) >= 5.0 or vol_ratio >= 5.0
            
            if is_anomaly and strength_score >= 30:
                now_time = datetime.now().strftime("%H:%M")
                # 傳送給 UI 的數據格式 (長度 8)
                # 時間, 強度, 趨勢, 幣種, 掛單比, 漲跌幅, 成交量, 資費
                data = (
                    now_time, 
                    f"{strength_score}pt", 
                    trend, 
                    display_name, 
                    obi, 
                    total_c, 
                    vol_ratio, 
                    funding_rate
                )
                
                side = 'long' if total_c >= 0 else 'short'
                self.ui_callback(side, data)

        except Exception:
            pass 

    async def main_loop(self):
        """全市場掃描主循環"""
        while self.is_running:
            self.status_callback("市場掃描中...")
            try:
                fr_all = await self.exchange.fetch_funding_rates()
                symbols = [s for s in fr_all.keys() if s.endswith('USDT')]

                # 增加 Orderbook 抓取後，建議 Semaphore 稍微調低保護 IP
                sem = asyncio.Semaphore(20)
                async def sem_task(s):
                    async with sem:
                        fr = fr_all[s]['fundingRate'] * 100 if s in fr_all else 0
                        await self.check_symbol_logic(s, fr)

                await asyncio.gather(*(sem_task(s) for s in symbols))
            except Exception as e:
                print(f"Loop Error: {e}")

            self.status_callback("等待中 (5分鐘週期)")
            await asyncio.sleep(300)