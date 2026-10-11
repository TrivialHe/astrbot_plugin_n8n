# n8n webhook

AstrBot 插件, 用于触发并调用n8n webhook

AstrBot plugin for triggering and calling n8n webhooks.

# 支持
## 调用方法

> [!note]
> 在对话中使用`/n8n`触发调用n8n, 比如`/n8n ob:#创意 #想法 #日志 可以做一个n8n的插件` 则会调用n8n webhook,内容是
> ```json
{
  "message": "ob:#创意 #想法 #日志 可以做一个n8n的插件",
  "senderName": "somebody"
}
> ```

### **1. 配置当前插件(同时配置n8n webhook)**  
**Endpoint:**  
`POST https://your-n8n-domain.com/webhook/your-path`  

**Basic Auth:**  
- `username: 'username-you-need-change'`
- `password: 'password-you-need-change'`

**Request Body (JSON):**  
```json
{
  "message": "消息内容或base64编码的图片",
  "senderName": "消息发送人"
}
```

**Response:**  
```json
{
  "success": true,
  "data": "n8n响应的message"
}
```
---

可以在n8n导入[n8n_webhook_example](./n8n_webhook_example.json)案例使用本插件对接

## 管理员与请求超时

`adminIds` 使用消息发送者 ID，多个以逗号分隔，逐项精确匹配。旧版本使用会话 ID 的子串匹配；升级前请将群号、会话标识或 ID 片段改为完整的发送者 ID。空白列表会拒绝调用。

请求最多等待 30 秒（连接最多 5 秒）。耗时工作流建议立即返回受理结果，后台继续执行。超时不代表任务未受理，插件不会自动重试，避免重复执行。失败时不向会话输出原始响应或异常详情。

开发验证（Python 使用 uv 管理，测试只请求临时本机 HTTP 服务）：

```sh
uv run --python 3.12 python -m unittest -v test_webhook.py
```
