# CloudMail邮箱API工具

[CloudMail](https://github.com/maillab/cloud-mail)是一个基于 Cloudflare 的简约响应式邮箱服务，支持邮件发送、附件收发

本插件是将 CloudMail API 集成到 Astrbot 的轻量插件，提供自助邮箱注册、邮件查询等功能，便于在QQ机器人中自动化处理与邮箱相关的操作。

## 主要功能
- 使用 CloudMail API 自动完成邮箱注册
- 查询和展示绑定邮箱的最新邮件

## 安装
1. 克隆本仓库
2. 在astrbot webUI界面进行安装,或者将插件文件夹拷贝到astrbot的plugins文件夹下后重启astrbot

## 配置
> 在WebUI的插件配置界面进行配置
- CloudMail邮箱地址：https://mail.example.com（末尾不带/）
- 管理员邮箱(admin email)，用于获取全局权限，例如 admin@example.com
- 管理员密码(admin_password)，管理员的登录密码
- 默认邮箱后缀 (email_domain)，在注册/绑定时自动补全

```json
{
  "api_base_url": {
    "description": "CloudMail邮箱地址",
    "type": "string",
    "hint": "例如 https://mail.example.com (末尾不带 /)"
  },
  "admin_email": {
    "description": "管理员邮箱",
    "type": "string",
    "hint": "用于获取全局权限，例如 admin@example.com"
  },
  "admin_password": {
    "description": "管理员密码",
    "type": "string",
    "hint": "管理员的登录密码",
    "obvious_hint": true
  },
  "email_domain": {
    "description": "默认邮箱后缀",
    "type": "string",
    "hint": "例如 @example.com，用于注册/绑定时自动补全"
  }
}
```

## 指令行为
| 行为类型     | 描述                                                                | 具体类型 | 触发方式 |
| :----------- | :------------------------------------------------------------------ | :------- | :------- |
| 平台消息下发时 | 自助注册, 格式为 /注册邮箱 <用户名> <密码>                          | 指令     | 注册邮箱 |
| 平台消息下发时 | 绑定已有邮箱, 格式为 /绑定邮箱 <邮箱用户名 (不需要@example.com) > | 指令     | 绑定邮箱 |
| 平台消息下发时 | 查询最新一封邮件, 格式为 /最新邮件                                  | 指令     | 最新邮件 |
| 平台消息下发时 | 测试管理员连接状态, 仅管理员可用，格式为 /邮件调试                    | 指令     | 邮件调试 |

## 贡献指南与后期规划

随缘更新，如果有感兴趣的可以fork本仓库向我PR

后续计划支持多邮箱后缀、管理员自助改密、如果cloud-mail项目有后续更新，进行相关的更新和适配

## 许可证

本项目采用 [MIT 许可证](LICENSE) 开源，详情请查阅许可证文件

![Star History Chart](https://api.star-history.com/svg?repos=WALKERKILLER/astrbot_plugin_cloudmailapi&type)