# -*- coding: utf-8 -*-
"""按官方推荐流程签名：先 cp 成 .shortcut，再 sign，失败则转 binary1 重试。"""
import plistlib, subprocess, os, shutil, uuid as uuidlib

OUT = '_signout'
os.makedirs(OUT, exist_ok=True)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()


def sign_with_retry(src_plist, tag):
    """官方推荐流程：
       1) cp source.plist → X.shortcut
       2) shortcuts sign -i X.shortcut -o out.shortcut
       3) 失败则 plutil -convert binary1 再试
    """
    work = f'_w_{tag}.shortcut'
    shutil.copyfile(src_plist, work)
    out = os.path.join(OUT, f'{tag}.shortcut')
    if os.path.exists(out):
        os.remove(out)

    attempts = []
    # 尝试1：直接签 .shortcut
    rc, so, se = run(['shortcuts', 'sign', '-i', work, '-o', out,
                       '-m', 'anyone', '-m', 'anyone'])
    attempts.append(('direct', rc, se or so))

    # 尝试2：转 binary1 再签
    if not os.path.exists(out):
        rc2, so2, se2 = run(['plutil', '-convert', 'binary1', work, '-o', work])
        rc3, so3, se3 = run(['shortcuts', 'sign', '-i', work, '-o', out,
                              '-m', 'anyone', '-m', 'anyone'])
        attempts.append(('binary_retry', rc3, se3 or so3))

    ok = os.path.exists(out) and os.path.getsize(out) > 0
    print(f'[{"OK  " if ok else "FAIL"}] {tag}')
    for name, rc, msg in attempts:
        m = (msg or '').strip().splitlines()
        m = m[0][:88] if m else ''
        print(f'        {name}: rc={rc} {m}')
    if ok:
        print(f'        → 产物 {out} ({os.path.getsize(out)} bytes)')
    return ok


def base_plist(name='test'):
    return {
        'WFWorkflowActions': [{
            'WFWorkflowActionIdentifier': 'is.workflow.actions.comment',
            'WFWorkflowActionParameters': {
                'WFCommentActionText': 'hi',
                'UUID': str(uuidlib.uuid4()).upper(),
            },
        }],
        'WFWorkflowClientVersion': '2607.0.3',
        'WFWorkflowClientRelease': '2.7',
        'WFWorkflowMinimumClientVersion': 900,
        'WFWorkflowMinimumClientVersionString': '900',
        'WFWorkflowName': name,
        'WFWorkflowIcon': {'WFWorkflowIconGlyphNumber': 59511,
                           'WFWorkflowIconStartColor': 4282601983},
        'WFWorkflowImportQuestions': [],
        'WFWorkflowInputContentItemClasses': [],
        'WFWorkflowTypes': ['NCWidget', 'WatchKit'],
    }


print('=== 1) 基础 plist（cp 成 .shortcut 后签）===')
with open('_b1.plist', 'wb') as f:
    plistlib.dump(base_plist(), f, fmt=plistlib.FMT_XML)
sign_with_retry('_b1.plist', 'basic')

print()
print('=== 2) 去掉 WFWorkflowIcon ===')
d = base_plist(); d.pop('WFWorkflowIcon')
with open('_b2.plist', 'wb') as f:
    plistlib.dump(d, f, fmt=plistlib.FMT_XML)
sign_with_retry('_b2.plist', 'no_icon')

print()
print('=== 3) WFWorkflowTypes 空 ===')
d = base_plist(); d['WFWorkflowTypes'] = []
with open('_b3.plist', 'wb') as f:
    plistlib.dump(d, f, fmt=plistlib.FMT_XML)
sign_with_retry('_b3.plist', 'empty_types')

print()
print('=== 4) 完全没有 UUID 键 ===')
d = base_plist()
d['WFWorkflowActions'][0]['WFWorkflowActionParameters'].pop('UUID')
with open('_b4.plist', 'wb') as f:
    plistlib.dump(d, f, fmt=plistlib.FMT_XML)
sign_with_retry('_b4.plist', 'no_uuid')

print()
print('=== 5) 最精简（只有 WFWorkflowActions + ClientVersion）===')
d = {'WFWorkflowActions': base_plist()['WFWorkflowActions'],
     'WFWorkflowClientVersion': '2607.0.3',
     'WFWorkflowInputContentItemClasses': []}
with open('_b5.plist', 'wb') as f:
    plistlib.dump(d, f, fmt=plistlib.FMT_XML)
sign_with_retry('_b5.plist', 'ultra_min')
