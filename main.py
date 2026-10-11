from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig
import asyncio
import re
import uuid
import aiohttp
from .commands import parse_command, to_command, validate_source


@register('astrbot_plugin_n8n', 'Wanxp', '明日方舟 MAA 自动化，支持每日任务、任务组合、AUTO 刷关卡和指定理智药数量', '1.2.0')
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    @filter.command('n8n')
    async def call_n8n(self, event: AstrMessageEvent):
        """固定 MAA 指令：maa daily 或 maa run fight stage=1-7 medicine=2。"""
        message = re.sub(r'^/?n8n(?:\s+|$)', '', event.message_str, count=1).strip()
        async for result in self.dispatch(event, message):
            yield result

    @filter.command('maa')
    async def maa_task(self, event: AstrMessageEvent, task: str = 'daily', stage: str = '', medicine: int = 0):
        """执行明日方舟任务。task=daily 表示今天每日任务，不含刷理智；task=fight 表示打开游戏刷关卡；task=startup 表示仅唤醒；也可用逗号组合 recruit,base,credit,award。所有任务最后关闭游戏。stage 为用户明确指定的关卡编号（如 1-7、CE-6、OF-1），空字符串代表上次关卡；medicine 是用户明确指定的理智药瓶数 0–99，未要求用药必须为 0，‘几瓶’需追问。刷关卡代理倍率 AUTO，不使用源石。"""
        try:
            if type(medicine) is not int or not 0 <= medicine <= 99 or not isinstance(task, str) or not isinstance(stage, str):
                raise ValueError('任务参数无效。')
            if task == 'daily':
                if medicine or stage:
                    raise ValueError('daily 不刷理智，关卡与用药请单独指定 fight。')
                selection = parse_command('maa daily')
            else:
                text = 'maa run ' + ' '.join(task.split(','))
                if stage: text += ' stage=' + stage.upper() if '@' not in stage and stage != 'Annihilation' else ' stage=' + stage
                if medicine: text += ' medicine=' + str(medicine)
                selection = parse_command(text)
            # Router preserves the original human request for grounding.
            if event.get_extra('ones_router_request', False):
                validate_source(selection, event.message_str)
        except ValueError as exc:
            event.stop_event()
            yield event.plain_result(str(exc))
            return
        async for result in self.dispatch(event, to_command(selection)):
            yield result

    async def dispatch(self, event, message):
        event.stop_event()
        cfg = self.config['n8n']
        platform = str(event.unified_msg_origin).split(':',1)[0]
        platforms = {v.strip() for v in cfg.get('allowedPlatformIds','').split(',') if v.strip()}
        senders = {v.strip() for v in cfg.get('adminIds','').split(',') if v.strip()}
        if platform not in platforms or str(event.get_sender_id()) not in senders:
            yield event.plain_result('你没有权限使用此自动化入口。')
            return
        try:
            selection = parse_command(message)
        except ValueError as exc:
            yield event.plain_result(str(exc))
            return
        request_id = str(uuid.uuid4())
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15,connect=5)) as session:
                async with session.post(cfg['n8n_webhook_url'],auth=aiohttp.BasicAuth(cfg['username'],cfg['password']),json={
                    'message':to_command(selection),'senderName':event.get_sender_name(),'senderId':str(event.get_sender_id()),
                    'platformId':platform,**selection,'umo':str(event.unified_msg_origin),'requestId':request_id,
                }) as response:
                    if response.status != 200:
                        logger.error(f'MAA request {request_id}: HTTP {response.status}')
                        yield event.plain_result('任务提交失败，请检查 n8n 连接。')
                        return
                    body = await response.json()
                    logger.info(f'MAA request {request_id}: accepted={body.get("success")}')
                    yield event.plain_result(str(body.get('data','任务响应异常，请检查日志。'))[:1200])
        except asyncio.TimeoutError:
            logger.warning(f'MAA request {request_id}: acknowledgment timeout')
            yield event.plain_result('请求确认超时，任务可能已受理，请勿立即重复提交。')
        except Exception:
            logger.exception(f'MAA request {request_id}: submission failed')
            yield event.plain_result('任务提交异常，请检查 AstrBot / n8n 日志。')
