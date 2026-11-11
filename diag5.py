# -*- coding: utf-8 -*-
"""定位并修复 shortcuts sign 的 'T@' (NSUUID) 类型错误。

思路：macOS 的 plist 解析器要求 UUID 类型是真正的 NSUUID（plistlib 用 uuid.UUID 对象写入）。
之前我们用普通字符串写 UUID/OutputUUID → 被当成 NSString 里的特殊标记解析失败。
"""
import plistlib, subprocess, os, uuid as uuidlib

OUT = '_signout'
os.makedirs(OUT, exist_ok=True)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()


def sign(path, name):
    out = os.path.join(OUT, name + '.shortcut')
    if os.path.exists(out):
        os.remove(out)
    rc, so, se = run(['shortcuts', 'sign', '-i', path, '-o', out,
                       '-m', 'anyone', '-m', 'anyone'])
    ok = os.path.exists(out) and os.path.getsize(out) > 0
    msg = (se or so or '').strip().splitlines()
    msg = msg[0][:80] if msg else ''
    print(f'[{"OK  " if ok else "FAIL"}] {name:28s} {msg}')
    return ok


def mk(path, use_uuid_obj, binary=False):
    u = uuidlib.uuid4()
    uuid_val = u if use_uuid_obj else str(u).upper()
    d = {
        'WFWorkflowActions': [{
            'WFWorkflowActionIdentifier': 'is.workflow.actions.comment',
            'WFWorkflowActionParameters': {
                'WFCommentActionText': 'hi',
                'UUID': uuid_val,
            },
        }],
        'WFWorkflowClientVersion': '2607.0.3',
        'WFWorkflowClientRelease': '2.7',
        'WFWorkflowMinimumClientVersion': 900,
        'WFWorkflowMinimumClientVersionString': '900',
        'WFWorkflowName': 'test',
        'WFWorkflowIcon': {'WFWorkflowIconGlyphNumber': 59511,
                           'WFWorkflowIconStartColor': 4282601983},
        'WFWorkflowImportQuestions': [],
        'WFWorkflowInputContentItemClasses': [],
        'WFWorkflowTypes': ['NCWidget', 'WatchKit'],
    }
    with open(path, 'wb') as f:
        plistlib.dump(d, f, fmt=plistlib.FMT_BINARY if binary else plistlib.FMT_XML)
    return path


print('=== UUID 用字符串 vs UUID 对象 ===')
sign(mk('_s.plist', False), 'uuid_string_xml')
sign(mk('_s2.plist', True), 'uuid_object_xml')
sign(mk('_s3.plist', True, binary=True), 'uuid_object_bin')
print()

print('=== UUID 对象 + 完整动作（含 attachmentsByRange）===')
u = uuidlib.uuid4()
out_uuid = uuidlib.uuid4()
d = {
    'WFWorkflowActions': [
        {
            'WFWorkflowActionIdentifier': 'is.workflow.actions.comment',
            'WFWorkflowActionParameters': {'WFCommentActionText': 'hi', 'UUID': u},
        },
        {
            'WFWorkflowActionIdentifier': 'is.workflow.actions.gettext',
            'WFWorkflowActionParameters': {
                'UUID': out_uuid,
                'WFInput': {
                    'Value': {
                        'string': '￼',
                        'attachmentsByRange': {
                            '{0, 1}': {
                                'Type': 'ActionOutput',
                                'OutputName': 'Comment',
                                'OutputUUID': out_uuid,
                                'Aggrandizements': [],
                            }
                        },
                    },
                    'WFSerializationType': 'WFTextTokenAttachment',
                },
            },
        },
    ],
    'WFWorkflowClientVersion': '2607.0.3',
    'WFWorkflowClientRelease': '2.7',
    'WFWorkflowMinimumClientVersion': 900,
    'WFWorkflowMinimumClientVersionString': '900',
    'WFWorkflowName': 'test2',
    'WFWorkflowIcon': {'WFWorkflowIconGlyphNumber': 59511,
                       'WFWorkflowIconStartColor': 4282601983},
    'WFWorkflowImportQuestions': [],
    'WFWorkflowInputContentItemClasses': [],
    'WFWorkflowTypes': ['NCWidget', 'WatchKit'],
}
with open('_full.plist', 'wb') as f:
    plistlib.dump(d, f, fmt=plistlib.FMT_XML)
sign('_full.plist', 'full_with_attachment')
