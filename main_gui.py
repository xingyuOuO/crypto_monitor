import asyncio
import threading
from tkinter import ttk
import customtkinter as ctk
from monitor_logic import CryptoMonitor # 匯入後端類別

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Crypto 動態異常監測終端")
        self.geometry("1300x820")
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
        
        self.start_btn = ctk.CTkButton(self.sidebar, text="START SCAN", height=45, fg_color="#28a745", 
                                       hover_color="#218838", font=("Arial", 14, "bold"), command=self.start)
        self.start_btn.pack(pady=15, padx=20)
        
        self.clear_btn = ctk.CTkButton(self.sidebar, text="CLEAR LOG", height=45, fg_color="#474D57", 
                                       hover_color="#2B2F36", font=("Arial", 14, "bold"), command=self.clear)
        self.clear_btn.pack(pady=10, padx=20)

        # --- 主顯示區域 ---
        self.container = ctk.CTkFrame(self, fg_color="#0B0E11", corner_radius=0)
        self.container.pack(side="right", fill="both", expand=True)

        self.status_bar = ctk.CTkLabel(self.container, text="STATUS: READY", font=("Consolas", 12), text_color="#707A8A")
        self.status_bar.pack(anchor="w", padx=20, pady=(15, 5))

        # 表格容器 (雙面板)
        self.panes = ctk.CTkFrame(self.container, fg_color="transparent")
        self.panes.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.long_tree = self.create_styled_tree(self.panes, "📈 BULLISH SIGNALS", "#00C076", "left")
        self.short_tree = self.create_styled_tree(self.panes, "📉 BEARISH SIGNALS", "#CF304A", "right")

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

        columns = ("時間", "EMA", "幣種", "漲跌幅", "成交量", "資費")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        
        widths = {"時間": 65, "EMA": 55, "幣種": 95, "漲跌幅": 90, "成交量": 90, "資費": 90}
        for col in columns:
            tree.heading(col, text=col, command=lambda c=col, t=tree: self.sort_column(t, c, False))
            tree.column(col, width=widths[col], anchor="center")
        
        tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        return tree

    def sort_column(self, tree, col, reverse):
        """實作點擊標題排序邏輯"""
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        try:
            # 針對數值類型（排除符號後）進行排序
            l.sort(key=lambda t: float(t[0].replace('%', '').replace('x', '').replace(':', '.')), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            tree.move(k, '', index)
        tree.heading(col, command=lambda: self.sort_column(tree, col, not reverse))

    def on_detected(self, side, data):
        """當發現訊號時，即時更新至表格最上方"""
        target = self.long_tree if side == 'long' else self.short_tree
        formatted = (data[0], data[1], data[2], f"{data[3]:.2f}%", f"{data[4]:.1f}x", f"{data[5]:.4f}%")
        target.insert("", 0, values=formatted)

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
            self.start_btn.configure(text="SCANNING...", state="disabled", fg_color="#474D57")

    def run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.monitor.main_loop())

if __name__ == "__main__":
    app = App()
    app.mainloop()