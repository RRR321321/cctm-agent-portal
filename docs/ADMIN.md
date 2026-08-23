# CCTM AGENT 平台 — 管理员手册

入口：http://192.168.2.88:8081/

## 账号

- 门户管理员（Django superuser）：`admin` / `123456`（内网临时口令，尽快在 /admin/ 修改）。
  管理员登录落 /stats/（统计页），/admin/ 可重置任意用户密码。
- `borui` 是普通用户（走注册流程开通），与同事账号同权。
- 同事账号：自助注册（名字拼音、无空格）。测试账号：cctest1/test12345、cctest2/newpass123、cctest3/test12345（可删）。

## 日常操作

| 操作 | 命令（在 .88 上） |
|---|---|
| 门户状态/重启 | `systemctl --user status/restart cctm-portal` |
| 看某用户实例日志 | `sudo journalctl -u qws@<名> -f` |
| 手动停/起实例 | `sudo systemctl stop/start qws@<名>`（停了用户再访问会自动拉起） |
| 写公共 SOP/模板 | `sudo cp 文件 /srv/cctm_agent_files/shared/`（用户只读） |
| 加共享 skill | 放到 `/srv/cctm_shared/skills/<skill名>/SKILL.md`（borui 在 cctm 组可直接写），**写后 `chmod 644`** 防组用户改写 |
| 删除用户 | Django admin 删用户 + `sudo userdel -r qws-<名>` + `sudo rm -rf /srv/cctm_agent_files/<名> /etc/cctm/{policy,instances,registry}/<名>.*` |
| 门户错误日志 | `/home/borui/cctm_portal/err.log` |

## 资源与限制（当前值，在 portal_project/settings.py 的 CCTM 块）

- 并发实例上限 10（满时 LRU 顶替最闲的）；空闲 20 分钟自动回收；
- 模型端真实并发上限 5（DGX gate 决定，统计页展示 N/5）；
- 每人会话上限 8（qws@ 单元 --max-sessions）；
- 上下文 100k 自动压缩（策略锁定 contextWindowSize=100000）。

## 安全边界（已验证）

用户实例沙箱：只能写自家 `/srv/cctm_agent_files/<名>` 与自家 home；内网全封（不能 ssh/隧道到别的机器）；
公网可用；无 sudo；读不到 /home/borui 与他人目录；模型自配置（Add Model/Delete/Set current//model//auth）全部禁用；
用户偷改 settings 加模型会被托管策略压制。

## 开机自启

cctm-portal、dgx-tunnel 均 enabled + linger=yes；qws@ 实例按需拉起（用户首次访问时）。
