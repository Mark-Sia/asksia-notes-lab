#!/bin/bash
# Poll for Shortcuts privacy/permission dialogs for $1 seconds and click Allow/OK. Logs actions.
END=$((SECONDS+${1:-20}))
while [ $SECONDS -lt $END ]; do
osascript <<'AS' 2>/dev/null
tell application "System Events"
  set out to ""
  repeat with p in (every application process whose visible is true)
    try
      repeat with w in (every window of p)
        set wn to ""
        try
          set wn to name of w
        end try
        if wn is missing value then set wn to ""
        set btns to {}
        try
          set btns to every button of w
        end try
        repeat with b in btns
          set bn to ""
          try
            set bn to name of b
          end try
          if bn is "Allow" or bn is "Always Allow" then
            click b
            set out to out & "clicked " & bn & " in " & (name of p) & "/" & wn & linefeed
          end if
        end repeat
        -- sheets inside windows
        try
          repeat with s in (every sheet of w)
            repeat with b in (every button of s)
              try
                if (name of b) is "Allow" then
                  click b
                  set out to out & "clicked Allow in sheet of " & (name of p) & linefeed
                end if
              end try
            end repeat
          end repeat
        end try
      end repeat
    end try
  end repeat
  if out is not "" then return out
end tell
AS
sleep 1
done
