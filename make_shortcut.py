#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build + sign 'AskSia Notes' — option A: one tap, zero pickers.
Input = the note's note.json URL. Produces, in this order:
  title → header (uni · term · discipline + tags) → the Sia visual INLINE → the full structured body → opens Notes.
Key facts proven on device 2026-08-30 (see KILL-TEST-2026-08-30.md):
  · Create Note takes its body on the legacy key WFCreateNoteInput
  · Add File (AddFileAttachmentLinkAction) inlines a real image and appends after the current content
  · Append to Note takes its text on the legacy key WFInput
python3 make_shortcut.py [--name="AskSia Notes"]
"""
import plistlib, uuid, subprocess, sys, os
NAME = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--name=")), "AskSia Notes")
B = "com.apple.mobilenotes"
U = [str(uuid.uuid4()).upper() for _ in range(12)]

def tok_input():
    return {"Value": {"attachmentsByRange": {"{0, 1}": {"Type": "ExtensionInput"}}, "string": "￼"}, "WFSerializationType": "WFTextTokenString"}
def tok(u, n):
    return {"Value": {"Type": "ActionOutput", "OutputUUID": u, "OutputName": n}, "WFSerializationType": "WFTextTokenAttachment"}
def tok_s(u, n):
    return {"Value": {"attachmentsByRange": {"{0, 1}": {"Type": "ActionOutput", "OutputUUID": u, "OutputName": n}}, "string": "￼"}, "WFSerializationType": "WFTextTokenString"}
def desc(i):
    return {"AppIntentIdentifier": i, "BundleIdentifier": B, "Name": "Notes", "TeamIdentifier": "0000000000"}
def get(u, src, key, out):
    return {"WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
            "WFWorkflowActionParameters": {"UUID": u, "WFInput": src, "WFGetDictionaryValueType": "Value",
                                           "WFDictionaryKey": key, "CustomOutputName": out}}
def fetch(u, url):
    return {"WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
            "WFWorkflowActionParameters": {"UUID": u, "WFURL": url, "WFHTTPMethod": "GET", "ShowHeaders": False}}

actions = [
    fetch(U[0], tok_input()),                                   # the note.json manifest
    get(U[1], tok(U[0], "Contents of URL"), "title",  "Title"),
    get(U[2], tok(U[0], "Contents of URL"), "header", "Header"),
    get(U[3], tok(U[0], "Contents of URL"), "img",    "Image URL"),
    get(U[4], tok(U[0], "Contents of URL"), "html",   "Body URL"),
    # 1 · the note, opened with the course header only
    {"WFWorkflowActionIdentifier": f"{B}.CreateNoteLinkAction",
     "WFWorkflowActionParameters": {"UUID": U[5], "AppIntentDescriptor": desc("CreateNoteLinkAction"),
                                    "name": tok_s(U[1], "Title"), "WFCreateNoteInput": tok_s(U[2], "Header")}},
    # 2 · the Sia visual, inlined right under the header
    fetch(U[6], tok_s(U[3], "Image URL")),
    {"WFWorkflowActionIdentifier": f"{B}.AddFileAttachmentLinkAction",
     "WFWorkflowActionParameters": {"UUID": U[7], "AppIntentDescriptor": desc("AddFileAttachmentLinkAction"),
                                    "name": "Sia visual", "file": tok(U[6], "Contents of URL"),
                                    "note": tok(U[5], "Create Note"), "WFNote": tok(U[5], "Create Note")}},
    # 3 · the structured body, appended below the visual
    fetch(U[8], tok_s(U[4], "Body URL")),
    {"WFWorkflowActionIdentifier": "is.workflow.actions.getrichtextfromhtml",
     "WFWorkflowActionParameters": {"UUID": U[9], "WFHTML": tok(U[8], "Contents of URL")}},
    {"WFWorkflowActionIdentifier": f"{B}.AppendToNoteLinkAction",
     "WFWorkflowActionParameters": {"UUID": U[10], "AppIntentDescriptor": desc("AppendToNoteLinkAction"),
                                    "WFNote": tok(U[5], "Create Note"), "note": tok(U[5], "Create Note"),
                                    "WFInput": tok_s(U[9], "Rich Text from HTML")}},
    # 4 · land the user in the finished note
    {"WFWorkflowActionIdentifier": f"{B}.OpenNoteLinkAction",
     "WFWorkflowActionParameters": {"UUID": U[11], "AppIntentDescriptor": desc("OpenNoteLinkAction"),
                                    "target": tok(U[5], "Create Note")}},
]
wf = {"WFWorkflowClientVersion": "2607.0.3", "WFWorkflowMinimumClientVersion": 900, "WFWorkflowMinimumClientVersionString": "900",
      "WFWorkflowIcon": {"WFWorkflowIconGlyphNumber": 59511, "WFWorkflowIconStartColor": 4274264319},
      "WFWorkflowTypes": ["NCWidget", "WatchKit"], "WFWorkflowInputContentItemClasses": ["WFStringContentItem", "WFURLContentItem"],
      "WFWorkflowHasShortcutInputVariables": True, "WFWorkflowHasOutputFallback": False, "WFWorkflowImportQuestions": [],
      "WFWorkflowActions": actions, "WFWorkflowName": NAME}
os.makedirs("dist", exist_ok=True)
raw, out = f"dist/{NAME}-unsigned.shortcut", f"dist/{NAME}.shortcut"
with open(raw, "wb") as f: plistlib.dump(wf, f, fmt=plistlib.FMT_BINARY)
r = subprocess.run(["shortcuts", "sign", "--mode", "anyone", "--input", raw, "--output", out], capture_output=True, text=True)
print("signed:", out, os.path.getsize(out) if os.path.exists(out) else "MISSING", "rc", r.returncode)
