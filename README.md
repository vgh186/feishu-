# 微信通知飞书助手

## 项目简介

微信通知飞书助手是一个用于将微信收到的院校类通知内容，通过AI（豆包API）自动提取关键信息（如标题、摘要、截止日期），并一键同步到飞书多维表格（Bitable）的桌面工具。适用于教务、行政等需要批量整理和归档微信通知的场景。

## 主要功能
- **批量粘贴微信通知**：支持多条通知内容自动分割与处理。
- **AI智能提取**：调用豆包API自动提取通知标题、摘要、截止日期。
- **自动写入飞书表格**：结构化数据自动同步到飞书Bitable。
- **历史记录管理**：本地保存所有处理记录，支持查询与详情查看。
- **图形化界面**：基于Tkinter，操作简单直观。

## 快速开始
1. 克隆本仓库到本地：
   ```bash
   git clone https://github.com/vgh186/feishu-.git
   ```
2. 安装依赖（如有）：
   ```bash
   pip install -r requirements.txt
   ```
3. 配置 `feishu_config.json`，填写豆包API和飞书Bitable相关信息。
4. 运行主程序：
   ```bash
   python wechat_feishu_gui.py
   ```

## 配置说明
- `feishu_config.json` 需包含如下字段：
  - `VOLC_API_KEY`、`VOLC_ENDPOINT_ID`（豆包API相关）
  - `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_BITABLE_APP_TOKEN`、`FEISHU_TABLE_ID`（飞书相关）

## 适用场景
- 教务、行政等需要批量整理和归档微信通知
- 需要将微信通知内容同步到飞书表格进行团队协作

## 许可证
MIT License

---
如有问题或建议，欢迎在GitHub Issue区留言。
