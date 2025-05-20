import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import json
import os
import datetime
import requests
import re
import sys
from pathlib import Path

# 确定配置文件路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的EXE运行
    application_path = os.path.dirname(sys.executable)
else:
    # 如果是脚本运行
    application_path = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(application_path, "feishu_config.json")
HISTORY_FILE = os.path.join(application_path, "notification_history.json")

# 全局变量
config = {}
VOLC_API_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# 字段映射
FIELD_MAPPING = {
    "院校通知": "院校通知",
    "院校通知详情 AI": "院校通知详情 AI",  # 修改这里
    "创建时间": "创建时间",
    "截止日期": "截止日期"
}

def load_config():
    """加载配置文件"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            messagebox.showerror("错误", f"配置文件 {CONFIG_FILE} 不存在！请确保配置文件在程序同目录下。")
            return {}
    except json.JSONDecodeError:
        messagebox.showerror("错误", f"配置文件 {CONFIG_FILE} 格式无效！")
        return {}
    except Exception as e:
        messagebox.showerror("错误", f"读取配置文件时发生错误: {e}")
        return {}

def save_to_history(notification_data):
    """保存处理记录到历史文件"""
    history = []
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
    except:
        history = []
    
    # 添加时间戳
    notification_data["处理时间"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 添加到历史记录
    history.append(notification_data)
    
    # 保存历史记录
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        messagebox.showerror("错误", f"保存历史记录时发生错误: {e}")

def load_history():
    """加载历史记录"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except:
        return []

def get_current_date_iso():
    """获取当前日期（ISO格式）"""
    return datetime.date.today().isoformat()

def extract_info_with_doubao_api(text):
    """使用豆包API提取通知信息"""
    global config
    
    VOLC_API_KEY = config.get("VOLC_API_KEY")
    VOLC_ENDPOINT_ID = config.get("VOLC_ENDPOINT_ID")
    
    if not VOLC_API_KEY or not VOLC_ENDPOINT_ID:
        messagebox.showerror("错误", "豆包API的 VOLC_API_KEY 或 VOLC_ENDPOINT_ID 未在配置中设置。")
        title = text.split("\n")[0][:60].strip()
        return {"title": title, "summary": text, "deadline": None}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VOLC_API_KEY}"
    }
    
    prompt = f"""请从以下通知文本中提取三个关键信息：通知标题、通知详情摘要和最晚截止日期。请严格按照以下JSON格式返回结果，确保所有字符串值都用双引号括起来。

关于"deadline"字段：
- 请识别文本中所有与截止相关的日期和时间表述。
- 如果有多个截止日期，请选择最晚的那一个。
- 如果截止日期只提到月份（例如"8月截止"），请将其转换为当年该月的最后一天（例如，如果当前是2025年，8月截止应为2025-08-31）。
- 如果截止日期是日期范围（例如"6月10日至6月20日"），请选择范围中的结束日期。
- 请将最终确定的最晚截止日期格式化为 YYYY-MM-DD。
- 如果文本中没有明确的截止日期，或无法按上述规则解析出有效截止日期，请将"deadline"字段的值设为 null。

关于"summary"字段：
- 请生成一个精简的通知详情摘要，确保不丢失原文的主要信息。
- **重要：摘要内容不应重复或包含已提取的"通知标题"中的文字。**

输出JSON格式：
{{
  "title": "提取的通知标题",
  "summary": "生成的通知详情摘要",
  "deadline": "YYYY-MM-DD格式的最晚截止日期或null"
}}

通知文本如下：
---开始---
{text}
---结束---

请严格按照上述JSON格式输出提取结果："""
    
    payload = {
        "model": VOLC_ENDPOINT_ID,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "temperature": 0.3 
    }
    
    extracted_data = {"title": None, "summary": text, "deadline": None}

    try:
        response = requests.post(VOLC_API_BASE_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        response_data = response.json()
        
        if response_data.get("choices") and len(response_data["choices"]) > 0:
            message_content = response_data["choices"][0].get("message", {}).get("content", "")
            try:
                if message_content.startswith("```json"):
                    message_content = message_content[7:]
                if message_content.endswith("```"):
                    message_content = message_content[:-3]
                message_content = message_content.strip()

                api_result = json.loads(message_content)
                extracted_data["title"] = api_result.get("title")
                extracted_data["summary"] = api_result.get("summary", text) 
                deadline_from_api = api_result.get("deadline")
                
                if deadline_from_api and isinstance(deadline_from_api, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", deadline_from_api):
                    extracted_data["deadline"] = deadline_from_api
                elif deadline_from_api is not None: 
                    print(f"警告：API返回的截止日期 \'{deadline_from_api}\' 不符合YYYY-MM-DD格式或为非null的无效值。将设置为None。")
                    extracted_data["deadline"] = None
                else: 
                    extracted_data["deadline"] = None

            except json.JSONDecodeError as je:
                print(f"错误：解析豆包API返回的JSON时出错: {je}。API原始响应: {message_content}")
                if not extracted_data.get("title"):
                    extracted_data["title"] = text.split("\n")[0][:60].strip()
            except Exception as inner_e:
                print(f"错误：处理API结果时发生意外错误: {inner_e}。API原始响应: {message_content}")
        else:
            print(f"错误：豆包API响应中未找到有效的choices。响应: {response_data}")
            
    except requests.exceptions.RequestException as e:
        print(f"错误：调用豆包API时发生网络或HTTP错误: {e}")
    except Exception as e:
        print(f"错误：处理豆包API响应时发生未知错误: {e}")
    
    return extracted_data

def is_new_notification_start(line_text):
    """判断是否是新通知的开始"""
    stripped_line = line_text.strip()
    if re.match(r"^[一二三四五六七八九十百千万]+：", stripped_line):
        return True
    if stripped_line.startswith("【"):
        if not re.match(r"^[一二三四五六七八九十百千万]+：\s*【", stripped_line):
            return True
    if re.match(r"^(重要)?通知：", stripped_line):
        return True
    return False

def split_notifications(text_block):
    """将文本块分割成多个通知"""
    lines = text_block.strip().split("\n")
    if not lines:
        return []
    notifications = []
    current_notification_lines = []
    first_content_line_found = False
    for line_content in lines:
        if not line_content.strip():
            if not first_content_line_found:
                continue
            current_notification_lines.append(line_content)
            continue
        if not first_content_line_found:
            first_content_line_found = True
        if current_notification_lines and is_new_notification_start(line_content):
            notifications.append("\n".join(current_notification_lines).strip())
            current_notification_lines = [line_content]
        else:
            current_notification_lines.append(line_content)
    if current_notification_lines:
        notifications.append("\n".join(current_notification_lines).strip())
    return [n for n in notifications if n.strip()]

def parse_single_notification(notification_text):
    """解析单条通知"""
    ai_extracted_info = extract_info_with_doubao_api(notification_text)
    
    title = ai_extracted_info.get("title")
    if not title:
        lines = notification_text.strip().split("\n")
        if lines:
            first_line_cleaned = lines[0].strip()
            match_bracket_title = re.match(r"^\s*【([^】]+)】", first_line_cleaned)
            if match_bracket_title:
                title = match_bracket_title.group(1).strip()
            else:
                title = first_line_cleaned.split("。")[0].split("\n")[0][:60].strip()
        if not title:
            title = "教学通知"
        title = title.replace("通知：", "").replace("通知:", "").strip()
    
    summary = ai_extracted_info.get("summary", notification_text)
    deadline_str = ai_extracted_info.get("deadline")

    return {
        "院校通知": title,
        "院校通知详情 AI": summary,
        "创建时间": get_current_date_iso(),
        "截止日期": deadline_str
    }

def get_tenant_access_token(app_id, app_secret):
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    headers = {"Content-Type": "application/json"}
    payload = {"app_id": app_id, "app_secret": app_secret}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        token_data = response.json()
        if "tenant_access_token" in token_data:
            return token_data["tenant_access_token"], None
        else:
            return None, token_data.get("msg", "获取token失败，未找到tenant_access_token")
    except requests.exceptions.RequestException as e:
        return None, f"获取token时发生网络错误: {e}"
    except json.JSONDecodeError:
        return None, "获取token时解析响应失败，非JSON格式"

def add_record_to_bitable(token, bitable_app_token, table_id, record_data):
    """向飞书多维表格添加记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{bitable_app_token}/tables/{table_id}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    fields_payload = {}
    for key, value in record_data.items():
        if key in FIELD_MAPPING:
            if (key == "截止日期" or key == "创建时间") and value and value != "未提取到截止日期" and value is not None:
                try:
                    dt_obj = datetime.datetime.strptime(value, "%Y-%m-%d")
                    fields_payload[FIELD_MAPPING[key]] = int(dt_obj.timestamp() * 1000)
                except ValueError:
                    print(f"警告：日期字段 \'{key}\' 的值 \'{value}\' 无法转换为时间戳，将跳过此字段。")
                    continue 
            else:
                if key == "截止日期" and (value == "未提取到截止日期" or value is None):
                    print(f"提示：字段 \'{key}\' 的值为 \'{value}\'，将不发送此字段给飞书。")
                    continue
                fields_payload[FIELD_MAPPING[key]] = value
        else:
            print(f"警告：数据中的键 \'{key}\' 在FIELD_MAPPING中未定义，将忽略此字段。")

    if not fields_payload:
        return False, "没有可写入的有效字段数据（可能是所有日期字段都无法转换或为空，或者所有字段都被忽略）。"

    payload = {"fields": fields_payload}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("code") == 0:
            return True, response_data.get("msg", "记录添加成功")
        else:
            error_detail = response_data.get("msg", "未知错误")
            if "data" in response_data and "record" in response_data["data"] and "id" in response_data["data"]["record"]:
                 error_detail += f" (记录ID: {response_data['data']['record']['id']})"
            elif "error" in response_data and "details" in response_data["error"]:
                error_detail += f" 详细: {response_data['error']['details']}"
            if response_data.get("code") == 1254064: 
                error_detail += " 这通常意味着发送的日期/时间格式不被飞书表格的日期列接受。脚本已尝试转换为毫秒级时间戳，请确保飞书表格中的日期列类型配置正确。"
            return False, f"添加记录失败 (code: {response_data.get('code')}): {error_detail}"

    except requests.exceptions.HTTPError as e:
        try:
            error_content = e.response.json()
            return False, f"添加记录时发生HTTP错误: {e.response.status_code} - {error_content}"
        except json.JSONDecodeError:
            return False, f"添加记录时发生HTTP错误: {e.response.status_code} - {e.response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"添加记录时发生网络错误: {e}"
    except json.JSONDecodeError:
        return False, "添加记录时解析响应失败，非JSON格式"

def write_to_feishu(record_data):
    """写入记录到飞书"""
    global config
    
    app_id = config.get("FEISHU_APP_ID")
    app_secret = config.get("FEISHU_APP_SECRET")
    bitable_app_token = config.get("FEISHU_BITABLE_APP_TOKEN")
    table_id = config.get("FEISHU_TABLE_ID")

    if not all([app_id, app_secret, bitable_app_token, table_id]):
        return False, "飞书配置信息不完整 (App ID, App Secret, Bitable App Token, or Table ID missing)."

    token, error_msg = get_tenant_access_token(app_id, app_secret)
    if error_msg:
        return False, f"获取飞书访问凭证失败: {error_msg}"
    if not token:
        return False, "获取飞书访问凭证失败，未收到Token但没有明确错误信息。"

    success, message = add_record_to_bitable(token, bitable_app_token, table_id, record_data)
    return success, message

class HistoryWindow(tk.Toplevel):
    """历史记录窗口"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("历史记录")
        self.geometry("800x600")
        self.minsize(600, 400)
        
        # 创建表格
        columns = ("处理时间", "院校通知", "院校通知详情 AI", "截止日期", "状态")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        
        # 设置列标题
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "院校通知详情 AI":
                self.tree.column(col, width=300)
            elif col == "院校通知":
                self.tree.column(col, width=200)
            else:
                self.tree.column(col, width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 加载历史记录
        self.load_history()
        
        # 双击查看详情
        self.tree.bind("<Double-1>", self.show_details)
    
    def load_history(self):
        """加载历史记录到表格"""
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 加载历史记录
        history = load_history()
        
        # 添加到表格
        for item in reversed(history):  # 最新的记录显示在前面
            status = item.get("状态", "未知")
            self.tree.insert("", "end", values=(
                item.get("处理时间", ""),
                item.get("院校通知", ""),
                item.get("院校通知详情 AI", "")[:100] + "..." if len(item.get("院校通知详情 AI", "")) > 100 else item.get("院校通知详情 AI", ""),
                item.get("截止日期", ""),
                status
            ))
    
    def show_details(self, event):
        """显示详细信息"""
        # 获取选中的项
        item_id = self.tree.selection()[0]
        item = self.tree.item(item_id)
        
        # 创建详情窗口
        detail_window = tk.Toplevel(self)
        detail_window.title("详细信息")
        detail_window.geometry("600x400")
        
        # 创建文本框
        text = scrolledtext.ScrolledText(detail_window, wrap=tk.WORD)
        text.pack(fill="both", expand=True)
        
        # 显示详细信息
        values = item["values"]
        text.insert(tk.END, f"处理时间: {values[0]}\n\n")
        text.insert(tk.END, f"院校通知: {values[1]}\n\n")
        text.insert(tk.END, f"院校通知详情 AI: {values[2]}\n\n")
        text.insert(tk.END, f"截止日期: {values[3]}\n\n")
        text.insert(tk.END, f"状态: {values[4]}\n")
        
        # 设置只读
        text.configure(state="disabled")

class App(tk.Tk):
    """主应用窗口"""
    def __init__(self):
        super().__init__()
        self.title("微信通知飞书助手")
        self.geometry("800x600")
        self.minsize(600, 400)
        
        # 加载配置
        global config
        config = load_config()
        
        # 创建主框架
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 创建标题标签
        title_label = tk.Label(self.main_frame, text="微信通知飞书助手", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 创建说明标签
        instruction_label = tk.Label(self.main_frame, text="请将微信通知内容粘贴到下方文本框，支持一次处理多条通知（系统会自动识别）")
        instruction_label.pack(pady=5)
        
        # 创建文本输入框
        self.text_input = scrolledtext.ScrolledText(self.main_frame, wrap=tk.WORD, height=15)
        self.text_input.pack(fill="both", expand=True, pady=10)
        
        # 创建按钮框架
        button_frame = tk.Frame(self.main_frame)
        button_frame.pack(fill="x", pady=10)
        
        # 创建提交按钮
        self.submit_button = tk.Button(button_frame, text="提交", command=self.process_notifications, width=10)
        self.submit_button.pack(side="left", padx=5)
        
        # 创建清空按钮
        self.clear_button = tk.Button(button_frame, text="清空", command=self.clear_text, width=10)
        self.clear_button.pack(side="left", padx=5)
        
        # 创建历史记录按钮
        self.history_button = tk.Button(button_frame, text="历史记录", command=self.show_history, width=10)
        self.history_button.pack(side="left", padx=5)
        
        # 创建状态框架
        status_frame = tk.Frame(self.main_frame)
        status_frame.pack(fill="x", pady=10)
        
        # 创建状态标签
        self.status_label = tk.Label(status_frame, text="就绪", anchor="w")
        self.status_label.pack(fill="x")
        
        # 创建结果文本框
        self.result_text = scrolledtext.ScrolledText(self.main_frame, wrap=tk.WORD, height=8)
        self.result_text.pack(fill="both", expand=True, pady=10)
        
        # 设置初始状态
        self.update_status("就绪，请粘贴微信通知内容")
    
    def update_status(self, message):
        """更新状态标签"""
        self.status_label.config(text=message)
        self.update_idletasks()
    
    def clear_text(self):
        """清空文本框"""
        self.text_input.delete(1.0, tk.END)
        self.result_text.delete(1.0, tk.END)
        self.update_status("已清空，请粘贴新的通知内容")
    
    def show_history(self):
        """显示历史记录"""
        history_window = HistoryWindow(self)
        history_window.transient(self)  # 设置为模态窗口
        history_window.grab_set()  # 获取焦点
        self.wait_window(history_window)  # 等待窗口关闭
    
    def process_notifications(self):
        """处理通知"""
        # 获取文本内容
        text = self.text_input.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "请先粘贴通知内容！")
            return
        
        # 清空结果文本框
        self.result_text.delete(1.0, tk.END)
        
        # 更新状态
        self.update_status("正在处理通知...")
        
        # 分割通知
        notifications = split_notifications(text)
        if not notifications:
            self.update_status("未能识别出任何通知，请检查输入内容")
            self.result_text.insert(tk.END, "未能识别出任何通知，请检查输入内容\n")
            return
        
        # 处理每条通知
        success_count = 0
        fail_count = 0
        
        for i, notification_text in enumerate(notifications):
            self.update_status(f"正在处理第 {i+1}/{len(notifications)} 条通知...")
            
            # 解析通知
            parsed_data = parse_single_notification(notification_text)
            
            # 显示解析结果
            self.result_text.insert(tk.END, f"--- 通知 {i+1}/{len(notifications)} ---\n")
            self.result_text.insert(tk.END, f"  院校通知: {parsed_data.get('院校通知')}\n")
            self.result_text.insert(tk.END, f"  院校通知详情 AI: {parsed_data.get('院校通知详情 AI')}\n")
            self.result_text.insert(tk.END, f"  创建时间: {parsed_data.get('创建时间')}\n")
            self.result_text.insert(tk.END, f"  截止日期: {parsed_data.get('截止日期')}\n")
            
            # 写入飞书
            success, message = write_to_feishu(parsed_data)
            
            # 添加状态信息
            parsed_data["状态"] = "成功" if success else f"失败: {message}"
            
            # 保存到历史记录
            save_to_history(parsed_data)
            
            # 显示写入结果
            if success:
                self.result_text.insert(tk.END, f"  写入结果: 成功\n\n")
                success_count += 1
            else:
                self.result_text.insert(tk.END, f"  写入结果: 失败 - {message}\n\n")
                fail_count += 1
            
            # 滚动到底部
            self.result_text.see(tk.END)
        
        # 更新最终状态
        if fail_count == 0:
            self.update_status(f"处理完成！成功写入 {success_count} 条通知")
        else:
            self.update_status(f"处理完成！成功 {success_count} 条，失败 {fail_count} 条")

if __name__ == "__main__":
    app = App()
    app.mainloop()
