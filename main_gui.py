import asyncio
import threading
from tkinter import ttk
import customtkinter as ctk
from monitor_logic import CryptoMonitor # 匯入後端類別

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Crypto 動態異常監測終端 v3.5")
        self.geometry("1600x850") # 稍微加寬以容納新欄位
        ctk.set_appearance_mode("dark")
        
        # 初始化後端監控實例
        self.monitor = CryptoMonitor(self.on_detected, self.update_status)
        self.setup_ui()

    def setup_ui(self):
        """配置介面佈局"""
        # --- 側邊控制列 ---
        self.sidebar = ctk.CTkFrame(self, width=180, corner_radius=0, fg_color="#1E2329")
        self.sidebar.pack(side="left", fill="y")
        
        ctk.CTkLabel(self.sidebar, text="SNIPER", font=("Impact", 32), text_color="#F0B90B").pack(pady=40)
        
        self.start_btn = ctk.CTkButton(self.sidebar, text="START...", height=45, fg_color="#28a745", 
                                       hover_color="#218838", font=("Arial", 14, "bold"), command=self.start)
        self.start_btn.pack(pady=15, padx=20)
        
        self.clear_btn = ctk.CTkButton(self.sidebar, text="CLEAR", height=45, fg_color="#474D57", 
                                       hover_color="#2B2F36", font=("Arial", 14, "bold"), command=self.clear)
        self.clear_btn.pack(pady=10, padx=20)

        # --- 指標說明框 ---
        self.guide_frame = ctk.CTkFrame(self.sidebar, fg_color="#2B2F36", corner_radius=10)
        self.guide_frame.pack(pady=20, padx=15, fill="x")

        ctk.CTkLabel(self.guide_frame, text="📊 指標說明", font=("Microsoft JhengHei", 16, "bold"), 
                     text_color="#F0B90B").pack(pady=(10, 5))

        # 強度說明
        guide_text = (
            "【強度評分】\n"
            "● 75-100: 極強訊號 (主力)\n"
            "● 50-75 : 標準強勢 (動能)\n"
            "● 30-50 : 弱勢波動 (警戒)\n\n"
            "──────────────────\n"
            "【掛單比 OBI 】\n"
            "  +0.6~1.0: 強勁買盤牆\n"
            "  +0.2~0.6: 偏多支撐\n"
            "  ±0.2以內: 勢均力敵\n"
            "  -0.2~-0.6: 偏空壓力\n"
            "  -0.6~-1.0: 沈重壓盤牆\n"
        )
        
        self.guide_label = ctk.CTkLabel(self.guide_frame, text=guide_text, font=("Microsoft JhengHei", 11), 
                                        justify="left", text_color="#EAECEF")
        self.guide_label.pack(pady=(0, 10), padx=10)

        # --- 主顯示區域 ---
        self.container = ctk.CTkFrame(self, fg_color="#0B0E11", corner_radius=0)
        self.container.pack(side="right", fill="both", expand=True)

        self.status_bar = ctk.CTkLabel(self.container, text="STATUS: READY", font=("Consolas", 12), text_color="#707A8A")
        self.status_bar.pack(anchor="w", padx=20, pady=(15, 5))

        # 表格容器 (雙面板)
        self.panes = ctk.CTkFrame(self.container, fg_color="transparent")
        self.panes.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.long_tree = self.create_styled_tree(self.panes, "📈 多頭趨勢", "#00C076", "left")
        self.short_tree = self.create_styled_tree(self.panes, "📉 空頭趨勢", "#CF304A", "right")

    def create_styled_tree(self, parent, title, color, side):
        """建立帶有滾動條與排序功能的專業表格"""
        frame = ctk.CTkFrame(parent, fg_color="#181A20", corner_radius=15)
        frame.pack(side=side, fill="both", expand=True, padx=8, pady=5)
        
        ctk.CTkLabel(frame, text=title, font=("Arial", 16, "bold"), text_color=color).pack(pady=15)
        
        # 定義表格樣式
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#181A20", foreground="#EAECEF", 
                        fieldbackground="#181A20", rowheight=32, font=("Arial", 11), borderwidth=0)
        style.configure("Treeview.Heading", background="#2B2F36", foreground="#707A8A", 
                        font=("Arial", 11, "bold"), borderwidth=0)
        style.map("Treeview", background=[('selected', '#323842')])

        # 新增 OBI 欄位
        columns = ("時間", "強度", "EMA", "幣種", "掛單比", "漲跌幅", "成交量", "資費")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        
        # 調整欄位寬度
        widths = {"時間": 60, "強度": 60, "EMA": 55, "幣種": 85, "掛單比": 85, "漲跌幅": 80, "成交量": 80, "資費": 80}
        for col in columns:
            tree.heading(col, text=col, command=lambda c=col, t=tree: self.sort_column(t, c, False))
            tree.column(col, width=widths[col], anchor="center")
        
        tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        return tree

    def sort_column(self, tree, col, reverse):
        """實作點擊標題排序邏輯"""
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        try:
            # 針對數值類型（排除符號與標籤後）進行排序
            l.sort(key=lambda t: float(t[0].replace('%', '').replace('x', '').replace('pt', '').replace(':', '.')), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            tree.move(k, '', index)
        tree.heading(col, command=lambda: self.sort_column(tree, col, not reverse))

    def on_detected(self, side, data):
        """當發現訊號時，檢查是否重複，若重複則更新，否則插入新數據"""
        target = self.long_tree if side == 'long' else self.short_tree
        
        # 幣種名稱在 data[3]
        symbol_to_check = data[3]
        
        # 格式化顯示數值 (對應表格 8 個欄位)
        formatted_values = (
            data[0],           # 時間
            data[1],           # 強度 (例如 "85pt")
            data[2],           # EMA 趨勢 (例如 "🟢↑")
            data[3],           # 幣種 (例如 "PEPE")
            f"{data[4]:+.2f}", # 掛單比 (OBI)，保留兩位並顯示正負號
            f"{data[5]:.2f}%", # 漲跌幅
            f"{data[6]:.1f}x", # 成交量倍數
            f"{data[7]:.4f}%"  # 資費
        )

        # --- 檢查重複並更新的邏輯 ---
        found = False
        for child in target.get_children():
            # 取得該列的「幣種」欄位值 (索引 3)
            existing_symbol = target.item(child)["values"][3]
            
            if existing_symbol == symbol_to_check:
                # 發現重複！用新的數據更新這一列
                target.item(child, values=formatted_values)
                # 更新後將該列移到最上方
                target.move(child, "", 0)
                found = True
                break
        
        # 如果沒找到重複的，就正常插入到最上方
        if not found:
            target.insert("", 0, values=formatted_values)

    def clear(self):
        """清空顯示內容"""
        for t in [self.long_tree, self.short_tree]:
            for i in t.get_children(): t.delete(i)

    def update_status(self, text):
        self.status_bar.configure(text=f"STATUS: {text.upper()}")

    def start(self):
        """按鈕觸發：啟動線程運行非同步主循環"""
        if not self.monitor.is_running:
            self.monitor.is_running = True
            threading.Thread(target=self.run_loop, daemon=True).start()
            self.start_btn.configure(text="START...", state="disabled", fg_color="#474D57")

    def run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.monitor.main_loop())

if __name__ == "__main__":
    app = App()
    app.mainloop()