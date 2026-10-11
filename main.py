import asyncio
import re

import aiohttp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.config.astrbot_config import AstrBotConfig


@register("astrbot_plugin_n8n", "Wanxp", "一个调用n8n webhook插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    async def initialize(self):
        pass

    @filter.command("n8n")
    async def call_n8n(self, event: AstrMessageEvent):
        """调用 n8n Webhook。adminIds 必须配置发送者 ID，而非群号或会话 ID。"""
        cfg = self.config["n8n"]
        admin_ids = {item.strip() for item in (cfg.get("adminIds") or "").split(",") if item.strip()}
        if not admin_ids:
            logger.error("n8n 插件未配置有效的 adminIds")
            yield event.plain_result("n8n 插件未配置 adminIds，请配置允许的发送者 ID，多个以逗号分隔。")
            return
        if str(event.get_sender_id()) not in admin_ids:
            logger.warning("未授权的发送者尝试调用 n8n 插件")
            return
        message = re.sub(r"^/?n8n(?:\s+|$)", "", event.message_str, count=1).strip()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30, connect=5)) as session:
                async with session.post(
                    url=cfg.get("n8n_webhook_url"),
                    auth=aiohttp.BasicAuth(cfg.get("username"), cfg.get("password")),
                    json={"message": message, "senderName": event.get_sender_name()},
                ) as response:
                    if response.status != 200:
                        logger.error(f"调用 n8n webhook 失败: HTTP {response.status}")
                        yield event.plain_result("调用 n8n webhook 失败，请检查配置或网络连接。")
                        return
                    data = await response.json()
                    if not isinstance(data, dict) or "data" not in data:
                        logger.warning("n8n 响应缺少 data 字段或 JSON 顶层不是对象")
                        yield event.plain_result("n8n 调用成功，但响应格式不正确，请检查 Webhook 的 data 字段。")
                        return
                    yield event.plain_result(f"n8n 返回结果: {data['data']}")
        except asyncio.TimeoutError:
            logger.warning("调用 n8n webhook 确认超时")
            yield event.plain_result("调用 n8n webhook 超时，任务可能已受理，请勿立即重复提交。")
        except (aiohttp.ContentTypeError, ValueError):
            logger.warning("n8n webhook 未返回有效 JSON")
            yield event.plain_result("n8n 响应不是有效 JSON，请检查 Webhook 响应配置。")
        except aiohttp.ClientError:
            logger.error("调用 n8n webhook 时发生网络错误")
            yield event.plain_result("调用 n8n webhook 时发生错误，请检查网络连接。")
        except Exception:
            logger.error("调用 n8n webhook 时发生异常，请检查插件配置")
            yield event.plain_result("调用 n8n webhook 时发生异常，请检查插件配置。")

    async def terminate(self):
        pass
