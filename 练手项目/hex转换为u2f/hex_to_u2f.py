import sys
import struct
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# 尝试导入 intelhex
try:
    from intelhex import IntelHex
except ImportError:
    import tkinter.messagebox

    root = tk.Tk()
    root.withdraw()
    tkinter.messagebox.showerror("缺少库", "请先安装 intelhex 库！\n\n在终端运行: pip install intelhex")
    sys.exit(1)

# ===========================
# 核心转换逻辑
# ===========================

UF2_MAGIC_START0 = 0x0A324655
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END = 0x0AB16F30
UF2_FLAG_FAMILY_ID_PRESENT = 0x00002000


def core_convert(input_hex, output_uf2, family_id, log_callback=None):
    if not os.path.exists(input_hex):
        raise FileNotFoundError("输入文件不存在")

    ih = IntelHex(input_hex)
    min_addr = ih.minaddr()
    max_addr = ih.maxaddr()

    # 对齐地址
    start_addr = min_addr - (min_addr % 256)

    if log_callback:
        log_callback(f"读取文件: {os.path.basename(input_hex)}")
        log_callback(f"地址范围: 0x{min_addr:08X} - 0x{max_addr:08X}")
        log_callback(f"Family ID: 0x{family_id:08X}")

    with open(output_uf2, 'wb') as f:
        total_data_len = max_addr - start_addr
        num_blocks = (total_data_len // 256) + 1

        block_no = 0
        curr_addr = start_addr

        while curr_addr <= max_addr:
            data = ih.tobinarray(start=curr_addr, size=256)
            if len(data) < 256:
                data += bytes([0xFF] * (256 - len(data)))

            flags = 0x00000000
            if family_id != 0:
                flags |= UF2_FLAG_FAMILY_ID_PRESENT

            header = struct.pack(
                "<IIIIIIII",
                UF2_MAGIC_START0,
                UF2_MAGIC_START1,
                flags,
                curr_addr,
                256,
                block_no,
                num_blocks,
                family_id
            )

            padding = bytes([0x00] * 220)
            footer = struct.pack("<I", UF2_MAGIC_END)

            block = header + data + padding + footer
            f.write(block)

            curr_addr += 256
            block_no += 1

    if log_callback:
        log_callback(f"转换完成! 共写入 {block_no} 个块。")
        log_callback(f"输出文件: {output_uf2}")


# ===========================
# GUI 界面代码
# ===========================

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("HEX 转 UF2 转换工具")
        self.root.geometry("600x450")
        self.root.resizable(False, False)

        # 常用 Family ID 字典
        self.family_ids = {
            "通用 / 无 (0x00000000)": 0x00000000,
            "RP2040 (Raspberry Pi Pico)": 0xe48bff56,
            "ESP32-S2": 0xbfdd4eee,
            "ESP32-S3": 0xc47e5767,
            "STM32F4": 0x57755a57,
            "SAMD21": 0x68ed2b88,
            "SAMD51": 0x55114460,
            "NRF52840": 0xada52840,
        }

        self.create_widgets()

    def create_widgets(self):
        # 容器 padding
        pad_opts = {'padx': 10, 'pady': 5}

        # --- 输入文件 ---
        input_frame = tk.LabelFrame(self.root, text="输入文件 (.hex)")
        input_frame.pack(fill="x", **pad_opts)

        self.input_path_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=self.input_path_var).pack(side="left", fill="x", expand=True, padx=5, pady=5)
        tk.Button(input_frame, text="选择文件...", command=self.select_input_file).pack(side="right", padx=5, pady=5)

        # --- 输出文件 ---
        output_frame = tk.LabelFrame(self.root, text="输出文件 (.uf2)")
        output_frame.pack(fill="x", **pad_opts)

        self.output_path_var = tk.StringVar()
        tk.Entry(output_frame, textvariable=self.output_path_var).pack(side="left", fill="x", expand=True, padx=5,
                                                                       pady=5)
        tk.Button(output_frame, text="另存为...", command=self.select_output_file).pack(side="right", padx=5, pady=5)

        # --- Family ID 选择 ---
        fam_frame = tk.LabelFrame(self.root, text="目标芯片 (Family ID)")
        fam_frame.pack(fill="x", **pad_opts)

        # 下拉框
        self.fam_combo = ttk.Combobox(fam_frame, values=list(self.family_ids.keys()), state="readonly")
        self.fam_combo.current(0)  # 默认选中第一个
        self.fam_combo.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        # 自定义 ID 输入框 (如果用户需要输入列表中没有的)
        tk.Label(fam_frame, text="或自定义 Hex:").pack(side="left", padx=5)
        self.custom_fam_var = tk.StringVar()
        tk.Entry(fam_frame, textvariable=self.custom_fam_var, width=15).pack(side="left", padx=5, pady=5)

        # --- 转换按钮 ---
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", pady=10)
        tk.Button(btn_frame, text="开始转换", command=self.start_conversion, bg="#DDDDDD", font=("Arial", 12, "bold"),
                  height=2).pack(fill="x", padx=20)

        # --- 日志区域 ---
        log_frame = tk.LabelFrame(self.root, text="日志")
        log_frame.pack(fill="both", expand=True, **pad_opts)

        self.log_text = tk.Text(log_frame, height=10, state="disabled", bg="#f0f0f0")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def select_input_file(self):
        filename = filedialog.askopenfilename(
            title="选择 HEX 文件",
            filetypes=[("Intel HEX", "*.hex"), ("All Files", "*.*")]
        )
        if filename:
            self.input_path_var.set(filename)
            # 自动生成输出文件名
            out_name = os.path.splitext(filename)[0] + ".uf2"
            self.output_path_var.set(out_name)

    def select_output_file(self):
        filename = filedialog.asksaveasfilename(
            title="保存 UF2 文件",
            defaultextension=".uf2",
            filetypes=[("UF2 Files", "*.uf2"), ("All Files", "*.*")]
        )
        if filename:
            self.output_path_var.set(filename)

    def start_conversion(self):
        inp = self.input_path_var.get()
        out = self.output_path_var.get()

        if not inp:
            messagebox.showwarning("提示", "请先选择输入文件！")
            return

        # 获取 Family ID
        try:
            custom_hex = self.custom_fam_var.get().strip()
            if custom_hex:
                # 优先使用自定义输入的 Hex
                fam_id = int(custom_hex, 16)
            else:
                # 使用下拉框的值
                selection = self.fam_combo.get()
                fam_id = self.family_ids[selection]
        except ValueError:
            messagebox.showerror("错误", "自定义 Family ID 格式错误，请输入十六进制 (如 0xe48bff56)")
            return

        # 执行转换
        self.log("-" * 30)
        try:
            core_convert(inp, out, fam_id, log_callback=self.log)
            messagebox.showinfo("成功", f"文件已转换并保存至:\n{out}")
        except Exception as e:
            self.log(f"错误: {str(e)}")
            messagebox.showerror("转换失败", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()