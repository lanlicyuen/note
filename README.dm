# 备忘录查询系统

## 技术栈
- Flask (Python)
- MySQL
- Discord Bot (discord.py)
- Android WebView (Java / Kotlin)

## API 设计
1. [POST] /login - 用户登录
2. [POST] /create_memo - 创建备忘录
3. [GET] /get_memos - 查询备忘录
4. [PUT] /update_memo - 更新备忘录

## Discord Bot 指令
- `/create` - 创建新备忘录
- `/update` 关键词 - 查询指定类别的记录
- `/list` - 查看所有记录