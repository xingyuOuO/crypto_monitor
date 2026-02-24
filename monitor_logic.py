import asyncio
import pandas as pd
from datetime import datetime
import ccxt.async_support as ccxt

class CryptoMonitor:
    def __init__(self, ui_callback, status_callback):
        self.ui_callback = ui_callback        # 發現訊號時的回調函式
        self.status_callback = status_callback  # 更新 UI 狀態的回調函式
        self.exchange = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
        self.is_running = False

    async def check_symbol_logic(self, symbol, funding_rate):
        """
        核心策略判斷邏輯：
        1. 15m EMA (7, 25, 99) 趨勢判定
        2. 5m 週期成交量倍率 (vs 1h 平均)
        3. 5m 週期漲跌幅 (單根或三根累計)
        """
        try:
            display_name = symbol.split(':')[0].replace('/USDT', '')
            
            # 抓取 K 線數據：15m 算趨勢，5m 算動量與成交量
            tasks = [
                self.exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100),
                self.exchange.fetch_ohlcv(symbol, timeframe='5m', limit=13)
            ]
            results = await asyncio.gather(*tasks)
            
            # --- 1. EMA 趨勢判定 (15分鐘週期) ---
            df15 = pd.DataFrame(results[0], columns=['ts','o','h','l','c','v'])
            curr_p = df15['c'].iloc[-1]
            e7, e25, e99 = [df15['c'].ewm(span=s, adjust=False).mean().iloc[-1] for s in [7, 25, 99]]
            
            trend = ""
            if curr_p > e7 and curr_p > e25 and curr_p > e99: trend = "🟢↑"
            elif curr_p < e7 and curr_p < e25 and curr_p < e99: trend = "🔴↓"

            # --- 2. 成交量與漲跌幅判定 (5分鐘週期) ---
            df5 = pd.DataFrame(results[1], columns=['ts','o','h','l','c','v'])
            
            # 計算 1 小時平均成交量 (前 12 根 5m K線)
            avg_v = df5['v'].iloc[-13:-1].mean()
            curr_v = df5['v'].iloc[-2] # 最近一根完成的 K 線
            vol_ratio = curr_v / avg_v if avg_v > 0 else 0

            # 計算漲跌幅 (最近三根已收盤 K 線)
            last3 = df5.iloc[-4:-1].copy()
            last3['chg'] = ((last3['c'] - last3['o']) / last3['o']) * 100
            max_c, min_c = last3['chg'].max(), last3['chg'].min()
            total_c = ((last3['c'].iloc[-1] - last3['o'].iloc[0]) / last3['o'].iloc[0]) * 100

            # --- 3. 觸發條件判定 ---
            # 條件：累計漲跌達 5% 或 單根達 5% 或 成交量爆發 5 倍
            if abs(total_c) >= 5.0 or max_c >= 5.0 or min_c <= -5.0 or vol_ratio >= 5.0:
                now_time = datetime.now().strftime("%H:%M")
                data = (now_time, trend, display_name, total_c, vol_ratio, funding_rate)
                
                # 根據總漲跌決定分類
                side = 'long' if total_c >= 0 else 'short'
                self.ui_callback(side, data)
                
        except Exception: 
            pass # 忽略單一幣種請求失敗

    async def main_loop(self):
        """全市場掃描主循環"""
        while self.is_running:
            self.status_callback("市場掃描中...")
            try:
                # 獲取所有合約的資費
                fr_all = await self.exchange.fetch_funding_rates()
                symbols = [s for s in fr_all.keys() if s.endswith('USDT')]
                
                # 使用 Semaphore 限制並發請求數，保護 IP
                sem = asyncio.Semaphore(25)
                async def sem_task(s):
                    async with sem:
                        fr = fr_all[s]['fundingRate'] * 100 if s in fr_all else 0
                        await self.check_symbol_logic(s, fr)
                
                await asyncio.gather(*(sem_task(s) for s in symbols))
            except Exception as e:
                print(f"Loop Error: {e}")
            
            self.status_callback("等待中 (5分鐘週期)")
            await asyncio.sleep(300)