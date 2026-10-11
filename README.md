# Ones MAA 维护版

这是 TrivialHe 针对本机 AstrBot → n8n → maa-cli 工作流维护的 fork。保留原作者与 AGPL-3.0 许可证；上游说明保留在本文末尾。

此版本将通用 Webhook 入口限制为固定 MAA 任务，不是原插件的通用替代品。

- `/maa daily`：每日流程，不包含刷理智。
- `/maa fight 1-7 2`：指定关卡及两瓶理智药；也支持 `task` 使用逗号组合 `recruit,base,credit,award`。
- `/n8n maa run fight stage=1-7 medicine=2`：固定命令入口。
- `adminIds` 配置允许的发送者 UID，`allowedPlatformIds` 配置允许的平台 ID；两项默认留空，必须在本机配置。
- Webhook 使用 Basic Auth；请求包含任务参数、UMO 与 requestId。n8n 应立即返回受理结果，再异步执行并发送最终结果。

`n8n_webhook_example.json` 仅测试消息往返，导入后须自行选择 Basic Auth 凭据；不会执行 MAA。

任务实现、排班、关闭游戏及刷关次数由独立的 n8n/MAA 后端决定，本仓库不包含后端、密钥或个人白名单。

---

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
