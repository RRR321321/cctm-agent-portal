#!/bin/bash
# 2026-08-23 文件管理权限迁移（root 执行一次）：
# 工作区改 私有组+2770(setgid)，门户用户进组，存量文件补组读写。
# 之后需重启 cctm-portal 与所有 qws@*（组成员/umask 为新进程生效）。
set -e
PORTAL_USER="${1:-borui}"
N=0
for conf in /etc/cctm/registry/*.conf; do
  [ -e "$conf" ] || continue
  NAME=$(basename "$conf" .conf)
  U="qws-$NAME"
  id "$U" >/dev/null 2>&1 || continue
  usermod -aG "$U" "$PORTAL_USER"
  D="/srv/cctm_agent_files/$NAME"
  if [ -d "$D" ]; then
    chown "$U:$U" "$D"
    chmod 2770 "$D"
    chmod -R g+rwX "$D"
    # skill 共享：项目级 skill 目录指向共享目录（与 provision 同步）
    mkdir -p "$D/.qwen"
    chown "$U:$U" "$D/.qwen"
    ln -sfn /srv/cctm_shared/skills "$D/.qwen/skills"
  fi
  N=$((N+1))
done
# 公共区改由门户代写代删（上传/删除走 Django，下载被禁）
SH="/srv/cctm_agent_files/shared"
[ -d "$SH" ] && chown "$PORTAL_USER:$PORTAL_USER" "$SH"
# 组变更对"已运行的 systemd user manager 及其子进程"不生效（manager 无 setgroups 特权），
# 必须从系统侧重启 user@UID，让 manager 带新组重生；cctm-portal 已 enable 会随之拉起。
UIDNU=$(id -u "$PORTAL_USER")
systemctl restart "user@$UIDNU.service"
sleep 3
runuser -u "$PORTAL_USER" -- env XDG_RUNTIME_DIR="/run/user/$UIDNU" \
  systemctl --user restart cctm-portal 2>/dev/null || true
for u in $(systemctl list-units 'qws@*' --state=active --no-legend | awk '{print $1}'); do
  systemctl restart "$u"
done
echo "OK migrated $N workspaces; user manager + portal + qws instances restarted"
