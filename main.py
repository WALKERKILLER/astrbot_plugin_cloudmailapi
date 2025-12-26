import aiohttp
import json
import re
import time
from datetime import datetime, timedelta, timezone
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("cloud_mail_plugin", "WalkerKiller", "CloudMail 邮件助手", "v1.0.0")
class CloudMailPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.user_binds = {}
        
        # 维护两个不同的 Token
        self.jwt_token = None      # 用于查信 (/api/login)
        self.toolbox_token = None  # 用于注册 (/api/public/genToken)
        self.jwt_expire = 0
        self.toolbox_expire = 0

    # ---------------- 辅助函数 ----------------
    def _get_api_url(self):
        return self.config.get("api_base_url", "").rstrip("/")

    def _get_domain(self):
        return self.config.get("email_domain", "")

    def _clean_html(self, raw_html):
        """清洗 HTML"""
        if not raw_html: return ""
        text = re.sub(r'<br\s*/?>', '\n', raw_html, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()

    def _convert_time(self, time_str):
        """将 UTC 时间转换为东八区时间"""
        if not time_str: return "未知时间"
        try:
            time_str = time_str.replace("Z", "+00:00")
            if "T" in time_str:
                dt = datetime.fromisoformat(time_str)
            else:
                dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            tz_cn = timezone(timedelta(hours=8))
            dt_cn = dt.astimezone(tz_cn)
            return dt_cn.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.warning(f"Time convert error: {e}")
            return time_str

    # ---------------- Token 获取逻辑 ----------------
    async def _get_jwt_token(self):
        """获取 JWT Token (用于查信)"""
        if self.jwt_token and time.time() < self.jwt_expire:
            return self.jwt_token

        base_url = self._get_api_url()
        email = self.config.get("admin_email")
        password = self.config.get("admin_password")
        if not base_url or not email or not password: return None

        # 查信必须用 /api/login
        url = f"{base_url}/api/login"
        payload = {"email": email, "password": password}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as resp:
                    res = await resp.json()
                    token = None
                    if isinstance(res, dict):
                        # 兼容处理
                        if "token" in res: token = res["token"]
                        elif "data" in res:
                            if isinstance(res["data"], str): token = res["data"]
                            elif isinstance(res["data"], dict): token = res["data"].get("token")
                    
                    if token:
                        self.jwt_token = token
                        self.jwt_expire = time.time() + 7200
                        return token
            except Exception as e:
                logger.error(f"JWT Login Error: {e}")
        return None

    async def _get_toolbox_token(self):
        """获取 Toolbox Token (用于注册)"""
        if self.toolbox_token and time.time() < self.toolbox_expire:
            return self.toolbox_token

        base_url = self._get_api_url()
        email = self.config.get("admin_email")
        password = self.config.get("admin_password")
        if not base_url or not email or not password: return None

        # 注册必须用 /api/public/genToken
        url = f"{base_url}/api/public/genToken"
        payload = {"email": email, "password": password}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as resp:
                    res = await resp.json()
                    token = None
                    # 解析 toolbox 返回格式
                    if isinstance(res, dict) and "data" in res:
                        data = res["data"]
                        if isinstance(data, dict): token = data.get("token")
                        elif isinstance(data, str): token = data
                    
                    if token:
                        self.toolbox_token = token
                        self.toolbox_expire = time.time() + 7200
                        return token
            except Exception as e:
                logger.error(f"Toolbox Token Error: {e}")
        return None

    # ---------------- 通用请求 ----------------
    async def _request(self, method, path, params=None, json_data=None, use_token_type="jwt"):
        base_url = self._get_api_url()
        if not base_url: return {"success": False, "msg": "未配置 api_base_url"}

        token = None
        if use_token_type == "jwt":
            token = await self._get_jwt_token()
        else:
            token = await self._get_toolbox_token()

        if not token:
            return {"success": False, "msg": f"获取 {use_token_type} Token 失败"}

        url = f"{base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": token  # 保持无 Bearer
        }

        async with aiohttp.ClientSession() as session:
            try:
                if method.upper() == "GET":
                    req = session.get(url, params=params, headers=headers)
                else:
                    req = session.post(url, json=json_data, headers=headers)

                async with req as resp:
                    if resp.status == 404:
                        return {"success": False, "msg": f"接口 404: {path}", "code": 404}
                    if resp.status == 401:
                        # 清除对应的缓存
                        if use_token_type == "jwt": self.jwt_token = None
                        else: self.toolbox_token = None
                        return {"success": False, "msg": "Token 失效", "code": 401}
                    
                    try:
                        return await resp.json()
                    except:
                        text = await resp.text()
                        return {"success": False, "msg": f"HTTP {resp.status}", "raw": text}
            except Exception as e:
                return {"success": False, "msg": str(e)}

    # ---------------- 指令：注册 ----------------
    @filter.command("注册邮箱")
    async def register_mail(self, event: AstrMessageEvent, username: str, password: str):
        """自助注册，格式为 /注册邮箱 <用户名> <密码>"""
        domain = self._get_domain()
        full_email = username if "@" in username else f"{username}{domain}"
        
        yield event.plain_result(f"正在注册 {full_email} ...")

        # 使用 Toolbox 接口和 Token
        payload = {"list": [{"email": full_email, "password": password}]}
        res = await self._request("POST", "/api/public/addUser", json_data=payload, use_token_type="toolbox")
        
        if res.get("code") == 200 or res.get("success") is True:
            user_id = event.get_sender_id()
            self.user_binds[user_id] = full_email
            yield event.plain_result(f"✅ 注册成功！\n账号: {full_email}\n已自动绑定，发送 /最新邮件 即可查信。")
        else:
            msg = res.get("msg") or res.get("message") or str(res)
            yield event.plain_result(f"❌ 注册失败: {msg}")

    # ---------------- 指令：绑定 ----------------
    @filter.command("绑定邮箱")
    async def bind_mail(self, event: AstrMessageEvent, email: str):
        """绑定已有邮箱，格式为 /绑定邮箱 <邮箱用户名（不需要@example.com）>"""
        domain = self._get_domain()
        full_email = email if "@" in email else f"{email}{domain}"
        
        user_id = event.get_sender_id()
        self.user_binds[user_id] = full_email
        yield event.plain_result(f"✅ 绑定成功！\n当前绑定: {full_email}")

    # ---------------- 指令：查信 ----------------
    @filter.command("最新邮件")
    async def check_latest_email(self, event: AstrMessageEvent):
        """查询最新一封邮件，格式为 /最新邮件"""
        user_id = event.get_sender_id()
        target_email = self.user_binds.get(user_id)

        if not target_email:
            yield event.plain_result("⚠️ 你还没有绑定邮箱。\n请使用 /注册邮箱 <用户> <密码> \n或 /绑定邮箱 <邮箱>")
            return

        params = {"userEmail": target_email, "size": "1", "type": "receive"}
        
        # 使用 JWT Token 查信
        res = await self._request("GET", "/api/allEmail/list", params=params, use_token_type="jwt")
        
        if res.get("code") == 404:
            res = await self._request("GET", "/api/email/allList", params=params, use_token_type="jwt")

        if res.get("success") is False:
            yield event.plain_result(f"⚠️ 查信失败: {res.get('msg')}")
            return

        mail_list = []
        data_field = res.get("data")
        if isinstance(data_field, dict) and "list" in data_field:
            mail_list = data_field["list"]
        elif isinstance(data_field, list):
            mail_list = data_field
        
        if not mail_list:
            yield event.plain_result(f"📭 邮箱 {target_email} 暂无邮件。")
            return

        latest = mail_list[0]
        
        # 解析信息
        subject = latest.get("subject", "无标题")
        sender_email = latest.get("sendEmail", "")
        sender_name = latest.get("name", "")
        
        if sender_name and sender_email: sender = f"{sender_name} <{sender_email}>"
        elif sender_name: sender = sender_name
        elif sender_email: sender = sender_email
        else: sender = "未知发件人"

        # 时间处理
        raw_time = latest.get("createTime") or latest.get("createdAt")
        display_time = self._convert_time(raw_time)

        # 内容处理
        content = ""
        if latest.get("text"): content = latest.get("text")
        elif latest.get("html"): content = self._clean_html(latest.get("html"))
        else: content = latest.get("intro") or "无内容"

        if len(content) > 1000:
            content = content[:1000] + "\n...(内容过长已截断)"

        msg_lines = [
            f"📧 最新邮件 ({target_email})",
            f"══════════════",
            f"发件人: {sender}",
            f"时  间: {display_time}",
            f"标  题: {subject}",
            f"══════════════",
            f"{content}"
        ]

        yield event.plain_result("\n".join(msg_lines))
        
    # ---------------- 调试 ----------------
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("邮件调试")
    async def debug_mail(self, event: AstrMessageEvent):
        """测试管理员连接状态，仅管理员可用格式为 /邮件调试"""
        token = await self._get_toolbox_token()
        if token:
            yield event.plain_result(f"✅ 管理员登录成功！Token前缀: {token[:10]}...")
        else:
            yield event.plain_result("❌ 管理员登录失败，请检查配置。")