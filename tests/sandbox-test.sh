#!/bin/bash
# 沙箱验证脚本：在 qws-cctest1 的单元命名空间内运行
echo "--- write /etc (expect DENIED)"
touch /etc/cctm_t 2>/dev/null && echo "!! ALLOWED (BAD)" || echo DENIED_OK
echo "--- read /home/borui (expect DENIED)"
ls /home/borui >/dev/null 2>&1 && echo "!! ALLOWED (BAD)" || echo DENIED_OK
echo "--- mkdir sibling under cctm_agent_files (expect DENIED)"
mkdir /srv/cctm_agent_files/other_t 2>/dev/null && echo "!! ALLOWED (BAD)" || echo DENIED_OK
echo "--- write shared (expect DENIED)"
touch /srv/cctm_agent_files/shared/t 2>/dev/null && echo "!! ALLOWED (BAD)" || echo DENIED_OK
echo "--- read shared (expect OK)"
ls -d /srv/cctm_agent_files/shared >/dev/null 2>&1 && echo READ_OK || echo "!! DENIED (BAD)"
echo "--- write own workspace (expect OK)"
touch /srv/cctm_agent_files/cctest1/t 2>/dev/null && echo WRITE_OK || echo "!! DENIED (BAD)"
echo "--- write own home (expect OK)"
touch /home/qws-cctest1/t 2>/dev/null && echo HOME_OK || echo "!! DENIED (BAD)"
echo "--- LAN curl DGX 219 (expect DENIED)"
curl -s -m 4 -o /dev/null http://192.168.2.219:8080/health 2>/dev/null && echo "!! LAN REACHABLE (BAD)" || echo LAN_DENIED_OK
echo "--- LAN curl self 192.168.2.88 (expect DENIED)"
curl -s -m 4 -o /dev/null http://192.168.2.88:8081/ 2>/dev/null && echo "!! LAN REACHABLE (BAD)" || echo LAN_DENIED_OK
echo "--- loopback portal (expect OK)"
code=$(curl -s -m 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/)
[ "$code" = "200" ] && echo LOOP_OK || echo "!! loopback fail: $code"
echo "--- public internet (expect OK)"
code=$(curl -s -m 10 -o /dev/null -w '%{http_code}' https://www.baidu.com)
[ "$code" = "200" ] && echo PUBLIC_OK || echo "!! public fail: $code"
echo "--- sudo attempt (expect DENIED)"
sudo -n true 2>/dev/null && echo "!! SUDO OK (BAD)" || echo SUDO_DENIED_OK
echo "--- ssh attempt (expect DENIED or no route)"
timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=3 wbrui@192.168.2.219 true 2>/dev/null && echo "!! SSH OK (BAD)" || echo SSH_DENIED_OK
echo SANDBOX_DONE
