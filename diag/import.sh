#!/bin/bash
f="$1"; name="$2"
open -a Shortcuts "$f"; sleep 4
raw=$(osascript -e 'tell application "System Events" to tell process "Shortcuts"
set frontmost to true
delay 0.3
repeat with w in windows
if (name of w) is "" or (name of w) is missing value then
set p to position of w
return ((item 1 of p) as integer) & " " & ((item 2 of p) as integer)
end if
end repeat
return "none"
end tell' 2>/dev/null | tr -d ',' | tr -s ' ')
if [ "$raw" != "none" ] && [ -n "$raw" ]; then
  x=$(echo $raw | awk '{print $1}'); y=$(echo $raw | awk '{print $2}')
  cliclick c:$((x+215)),$((y+135)); sleep 3
fi
shortcuts list | grep -c "^$name\$"
