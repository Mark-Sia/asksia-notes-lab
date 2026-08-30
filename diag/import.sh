#!/bin/bash
# import a signed .shortcut: open it, locate the import dialog (unnamed Shortcuts window), click "Add Shortcut"
f="$1"; name="$2"
open -a Shortcuts "$f"; sleep 4
pos=$(osascript -e 'tell application "System Events" to tell process "Shortcuts"
set frontmost to true
delay 0.3
repeat with w in windows
if (name of w) is "" or (name of w) is missing value then
set p to position of w
set s to size of w
return ((item 1 of p) as text) & "," & ((item 2 of p) as text) & "," & ((item 1 of s) as text) & "," & ((item 2 of s) as text)
end if
end repeat
return "none"
end tell' 2>/dev/null)
echo "dialog=$pos"
if [ "$pos" != "none" ] && [ -n "$pos" ]; then
  x=$(echo $pos | cut -d, -f1); y=$(echo $pos | cut -d, -f2)
  cliclick c:$((x+215)),$((y+135)); sleep 3
fi
shortcuts list | grep -c "^$name\$"
