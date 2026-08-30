#!/bin/bash
# iphone.sh — 安全控制 iPhone（经 macOS iPhone Mirroring 窗口）
#
# 安全设计（这才是"安全"的实质，不是口头保证）：
#   1. 每次动作都重新读取镜像窗口的实时位置 —— 绝不使用缓存坐标（窗口被移动也不会点错）
#   2. 坐标一律是"窗口内相对值"，越界（<0 或 > 窗口宽高）直接 exit 1，不发送任何点击
#   3. 点击前把窗口置前；点击后自动截图，便于逐步核验
#   4. 只截取窗口矩形，不截你的整个桌面
#   5. 无窗口 = 拒绝执行
#
# 用法:
#   ./iphone.sh rect                 打印窗口矩形
#   ./iphone.sh shot [out.png]       截图（只含手机屏幕）
#   ./iphone.sh tap <rx> <ry> [out]  点击窗口内相对坐标
#   ./iphone.sh swipe <x1> <y1> <x2> <y2> [ms]
#   ./iphone.sh type "text"
#   ./iphone.sh key <keyname>        例: return / escape / home
set -euo pipefail
SHOTDIR="${SHOTDIR:-$(cd "$(dirname "$0")" && pwd)/preview}"
mkdir -p "$SHOTDIR"

rect() {
  osascript -e 'tell application "System Events" to tell process "iPhone Mirroring"
    if (count of windows) = 0 then return "NOWINDOW"
    set w to window 1
    set p to position of w
    set s to size of w
    return ((item 1 of p) as integer) & " " & ((item 2 of p) as integer) & " " & ((item 1 of s) as integer) & " " & ((item 2 of s) as integer)
  end tell' 2>/dev/null | tr -d ',' | tr -s ' '
}

read_rect() {
  R=$(rect)
  if [ "$R" = "NOWINDOW" ] || [ -z "$R" ]; then
    echo "REFUSED: iPhone Mirroring 没有可见窗口 — 不发送任何输入" >&2; exit 1
  fi
  WX=$(echo "$R" | awk '{print $1}'); WY=$(echo "$R" | awk '{print $2}')
  WW=$(echo "$R" | awk '{print $3}'); WH=$(echo "$R" | awk '{print $4}')
}

guard() {  # 硬边界：相对坐标必须落在窗口内
  local rx=$1 ry=$2
  if [ "$rx" -lt 0 ] || [ "$ry" -lt 0 ] || [ "$rx" -gt "$WW" ] || [ "$ry" -gt "$WH" ]; then
    echo "REFUSED: ($rx,$ry) 超出手机窗口 ${WW}x${WH} — 拒绝点击，防止误触窗口外的东西" >&2; exit 1
  fi
}

front() { osascript -e 'tell application "iPhone Mirroring" to activate' >/dev/null 2>&1; sleep 0.4; }

shot() {
  read_rect
  local out="${1:-$SHOTDIR/iphone-$(date +%H%M%S).png}"
  screencapture -x -R "$WX,$WY,$WW,$WH" "$out"
  echo "$out"
}

case "${1:-}" in
  rect) read_rect; echo "x=$WX y=$WY w=$WW h=$WH" ;;
  shot) shot "${2:-}" ;;
  tap)
    read_rect; guard "$2" "$3"; front
    cliclick c:$((WX+$2)),$((WY+$3))
    sleep 1.2; shot "${4:-}" ;;
  swipe)
    read_rect; guard "$2" "$3"; guard "$4" "$5"; front
    cliclick m:$((WX+$2)),$((WY+$3)) dd:$((WX+$2)),$((WY+$3)) w:${6:-260} m:$((WX+$4)),$((WY+$5)) w:120 du:$((WX+$4)),$((WY+$5))
    sleep 1.2; shot "${7:-}" ;;
  type)
    read_rect; front
    osascript -e "tell application \"System Events\" to tell process \"iPhone Mirroring\" to keystroke \"$2\""
    sleep 1.0; shot "${3:-}" ;;
  key)
    read_rect; front
    osascript -e "tell application \"System Events\" to tell process \"iPhone Mirroring\" to key code $2"
    sleep 1.0; shot "${3:-}" ;;
  *) sed -n '2,22p' "$0" ;;
esac
