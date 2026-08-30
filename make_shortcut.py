#!/usr/bin/env python3
"""Build + sign the 'AskSia Notes' shortcut (format verified against Shortcuts' own DB serialization, 2026-08-30).
Shortcut Input (text) = "<note title>\n<payload url>"
  Split Text → title / url → Get Contents of URL → Get Rich Text from HTML → Create Note(name, WFCreateNoteInput=rich) → Open Note
python3 make_shortcut.py [--name=X] [--no-open]"""
import plistlib, uuid, subprocess, sys, os
NAME = next((a.split("=",1)[1] for a in sys.argv if a.startswith("--name=")), "AskSia Notes")
OPEN = "--no-open" not in sys.argv
B = "com.apple.mobilenotes"
U = [str(uuid.uuid4()).upper() for _ in range(8)]
def tok_input(): return {"Value": {"attachmentsByRange": {"{0, 1}": {"Type": "ExtensionInput"}}, "string": "￼"}, "WFSerializationType": "WFTextTokenString"}
def tok_out(uid, name): return {"Value": {"Type": "ActionOutput", "OutputUUID": uid, "OutputName": name}, "WFSerializationType": "WFTextTokenAttachment"}
def tok_out_str(uid, name): return {"Value": {"attachmentsByRange": {"{0, 1}": {"Type": "ActionOutput", "OutputUUID": uid, "OutputName": name}}, "string": "￼"}, "WFSerializationType": "WFTextTokenString"}
def desc(i): return {"AppIntentIdentifier": i, "BundleIdentifier": B, "Name": "Notes", "TeamIdentifier": "0000000000"}
actions = [
 {"WFWorkflowActionIdentifier": "is.workflow.actions.text.split", "WFWorkflowActionParameters": {"UUID": U[0], "text": tok_input(), "WFTextSeparator": "New Lines"}},
 {"WFWorkflowActionIdentifier": "is.workflow.actions.getitemfromlist", "WFWorkflowActionParameters": {"UUID": U[1], "WFInput": tok_out(U[0], "Split Text"), "WFItemSpecifier": "First Item", "CustomOutputName": "Note Title"}},
 {"WFWorkflowActionIdentifier": "is.workflow.actions.getitemfromlist", "WFWorkflowActionParameters": {"UUID": U[2], "WFInput": tok_out(U[0], "Split Text"), "WFItemSpecifier": "Last Item", "CustomOutputName": "Payload URL"}},
 {"WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl", "WFWorkflowActionParameters": {"UUID": U[3], "WFURL": tok_out_str(U[2], "Payload URL"), "WFHTTPMethod": "GET", "ShowHeaders": False}},
 {"WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey", "WFWorkflowActionParameters": {"UUID": U[7], "WFInput": tok_out(U[3], "Contents of URL"), "WFGetDictionaryValueType": "Value", "WFDictionaryKey": "md", "CustomOutputName": "Markdown"}},
 {"WFWorkflowActionIdentifier": "is.workflow.actions.getrichtextfrommarkdown", "WFWorkflowActionParameters": {"UUID": U[4], "WFInput": tok_out(U[7], "Markdown")}},
 {"WFWorkflowActionIdentifier": "com.apple.mobilenotes.SharingExtension", "WFWorkflowActionParameters": {"UUID": U[5], "AppIntentDescriptor": desc("CreateNoteLinkAction"),
      "name": tok_out_str(U[1], "Note Title"), "WFCreateNoteInput": tok_out_str(U[4], "Rich Text from Markdown"), "ShowWhenRun": False}},
]
if OPEN:
    actions.append({"WFWorkflowActionIdentifier": "is.workflow.actions.openapp", "WFWorkflowActionParameters": {"UUID": U[6], "WFAppIdentifier": B, "WFSelectedApp": {"BundleIdentifier": B, "Name": "Notes", "TeamIdentifier": "0000000000"}}})
wf = {"WFWorkflowClientVersion": "2607.0.3", "WFWorkflowMinimumClientVersion": 900, "WFWorkflowMinimumClientVersionString": "900",
      "WFWorkflowIcon": {"WFWorkflowIconGlyphNumber": 59511, "WFWorkflowIconStartColor": 4274264319},
      "WFWorkflowTypes": ["NCWidget", "WatchKit"], "WFWorkflowInputContentItemClasses": ["WFStringContentItem", "WFURLContentItem"],
      "WFWorkflowHasShortcutInputVariables": True, "WFWorkflowHasOutputFallback": False, "WFWorkflowImportQuestions": [],
      "WFWorkflowActions": actions, "WFWorkflowName": NAME}
os.makedirs("dist", exist_ok=True)
raw, out = f"dist/{NAME}-unsigned.shortcut", f"dist/{NAME}.shortcut"
with open(raw, "wb") as f: plistlib.dump(wf, f, fmt=plistlib.FMT_BINARY)
r = subprocess.run(["shortcuts", "sign", "--mode", "anyone", "--input", raw, "--output", out], capture_output=True, text=True)
print("signed:", out, os.path.getsize(out) if os.path.exists(out) else "MISSING", "| rc", r.returncode)
