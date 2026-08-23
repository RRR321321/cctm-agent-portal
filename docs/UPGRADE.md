# CCTM AGENT 平台 — qwen-code 升级手册

同事平台的所有"配置/限制/UI 修改"都**不放在 qwen-code 安装包内**，因此升级 qwen 不会丢失任何东西。
但升级后必须回归验证注入脚本依赖的 DOM 锚点（见第 4 节）。

## 1. 架构回顾（为什么升级安全）

- 程序：`/opt/cctm/qwen/versions/<版本>/` + `current` 软链。实例单元 `qws@<用户>.service` 从 `current` 启动。
  **实例不经过 npm launcher，没有自动更新**；策略里 `general.enableAutoUpdate=false` 双保险。
- 配置：每用户 `/etc/cctm/policy/<用户>.json`（托管设置，合并优先级最高）+ HOME 骨架。
- UI：Django 代理层注入（`static/portal/inject.*`），安装包零补丁。
- 门户：`/home/borui/cctm_portal`（独立 Django 工程）。

## 2. 升级步骤

```bash
# 0) 新版本来源：borui 自己的 qwen 会自动下载到 ~/.qwen/updates/npm/*/versions/<ver>/
#    （或手动 npm pack 解压）。确认该目录 web-shell 是原版（本方案不打补丁）。
V=0.22.0   # 举例

# 1) 复制为版本化安装（root）
sudo mkdir -p /opt/cctm/qwen/versions
sudo cp -a ~/.qwen/updates/npm/*/versions/$V /opt/cctm/qwen/versions/
sudo chmod -R a+rX /opt/cctm/qwen/versions/$V

# 2) 先在金丝雀用户上验证（selftest1 专为此保留）
sudo ln -sfn /opt/cctm/qwen/versions/$V/node_modules/@qwen-code/qwen-code /opt/cctm/qwen/current
sudo systemctl restart qws@selftest1

# 3) 回归验证（在 .88 上跑，需 venv 里的 playwright）
/home/borui/cctm_portal/venv/bin/python /home/borui/cctm_portal/tests/ui_test.py      # 遮罩/注册/导航/统计
/home/borui/cctm_portal/venv/bin/python /home/borui/cctm_portal/tests/ui_effort2.py   # 思考档位 Extra High/Max 置灰
# 重点看：[1][2][3][5] 全 True；effort options 中 Extra High/Max disabled=True

# 4) 验证失败 → 回滚
sudo ln -sfn /opt/cctm/qwen/versions/<旧版本>/node_modules/@qwen-code/qwen-code /opt/cctm/qwen/current
sudo systemctl restart qws@selftest1

# 5) 验证通过 → 滚动重启所有在跑实例（或等空闲回收自然换版本）
for u in $(systemctl list-units 'qws@*' --state=active --no-legend | awk '{print $1}'); do
  sudo systemctl restart $u
done
```

## 3. 门户（Django）升级

```bash
# 本地改完 rsync 到 .88（排除运行时文件）
rsync -az --delete --exclude db.sqlite3 --exclude .secret_key --exclude .dgx_key \
      --exclude venv --exclude static/portal/vendor --exclude err.log \
      cctm_portal/ borui@192.168.2.88:/home/borui/cctm_portal/
ssh borui@192.168.2.88 'systemctl --user restart cctm-portal'
```

## 4. 注入脚本依赖的 DOM 锚点（qwen 大改版时逐项核对）

| 锚点 | 用途 | 失效表现 |
|---|---|---|
| `</head>` | 注入点 | 导航条/置灰全失效 |
| `[role=combobox][aria-label="Reasoning Effort"]` 及选项文本 `Extra High`/`Max` | 思考档位 | 高档位可选 |
| 按钮文本 `+ Add Model` / `Delete` / `Set current` | 模型锁 | 用户可改模型 |
| class 含 `brandName`/`title` 叶子节点文本 `Qwen Code`；class 含 `subtitle` 的欢迎语 | 品牌文案替换 | 显示回 Qwen Code 原文 |
| `.cm-content` composer | （测试脚本用） | 仅影响测试 |
| `button[aria-label="Settings"]` | （测试脚本用） | 仅影响测试 |

若 qwen 改版改了标签文案（如 Extra High → XHigh），同步更新 `inject.js` 的 `BAD` 正则。

## 5. 其他不变量（勿动）

- `qws@.service` 沙箱段（ProtectSystem/strict、IPAddressDeny 内网段等）；
- `/etc/sudoers.d/cctm` 仅放行 systemctl qws@* 与 cctm-provision；
- 共享 skills 目录 `/srv/cctm_shared/skills`（3775 root:cctm，sticky）；
- 公共只读区 `/srv/cctm_agent_files/shared`（755 root，仅 root 可写）。
