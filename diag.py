# -*- coding: utf-8 -*-
"""诊断 shortcuts sign 拒绝文件的原因：逐个变体试签。"""
import plistlib, subprocess, sys, os, shutil

SRC = '推送健康数据.plist'
base = plistlib.load(open(SRC, 'rb'))

def try_sign(name, path):
    out = f'_t_{name}.shortcut'
    if os.path.exists(out):
        os.remove(out)
    r = subprocess.run(['shortcuts', 'sign', '-i', path, '-o', out,
                        '-m', 'anyone', '-m', 'anyone'],
                       capture_output=True, text=True)
    ok = os.path.exists(out)
    msg = (r.stderr or r.stdout or '').strip().splitlines()
    msg = msg[0] if msg else ''
    print(f'[{"OK " if ok else "FAIL"}] {name:32s} {msg[:90]}')
    return ok

def dump(d, path, binary=False):
    fmt = plistlib.FMT_BINARY if binary else plistlib.FMT_XML
    with open(path, 'wb') as f:
        plistlib.dump(d, f, fmt=fmt)
    return path

print('=== 0) 基础信息 ===')
print('顶层键:', sorted(base.keys()))
print('动作数:', len(base['WFWorkflowActions']))
print('WFWorkflowTypes:', base.get('WFWorkflowTypes'))
print()

print('=== 1) 最小 plist（只有注释动作）===')
mini = {
    'WFWorkflowActions': [{
        'WFWorkflowActionIdentifier': 'is.workflow.actions.comment',
        'WFWorkflowActionParameters': {'WFCommentActionText': 'hi'},
    }],
    'WFWorkflowClientVersion': '2607.0.3',
    'WFWorkflowTypes': ['NCWidget', 'WatchKit'],
    'WFWorkflowInputContentItemClasses': [],
}
try_sign('minimal_xml', dump(mini, '_mini.plist'))
try_sign('minimal_bin', dump(mini, '_mini_bin.plist', binary=True))
print()

print('=== 2) 原样 plist 转 binary 再签 ===')
try_sign('orig_bin', dump(base, '_orig_bin.plist', binary=True))
print()

print('=== 3) 变体：WFWorkflowTypes 非空 ===')
v = dict(base); v['WFWorkflowTypes'] = ['NCWidget', 'WatchKit']
try_sign('types_nonempty', dump(v, '_v_types.plist'))
print()

print('=== 4) 变体：去掉 WFWorkflowName ===')
v2 = {k: val for k, val in base.items() if k != 'WFWorkflowName'}
try_sign('no_name', dump(v2, '_v_noname.plist'))
print()

print('=== 5) 变体：两个都去 ===')
v3 = {k: val for k, val in base.items() if k not in ('WFWorkflowName',)}
v3['WFWorkflowTypes'] = ['NCWidget', 'WatchKit']
try_sign('no_name_types', dump(v3, '_v_both.plist'))
print()

print('=== 6) 变体：只保留核心键 ===')
core = {
    'WFWorkflowActions': base['WFWorkflowActions'],
    'WFWorkflowClientVersion': base.get('WFWorkflowClientVersion', '2607.0.3'),
    'WFWorkflowClientRelease': base.get('WFWorkflowClientRelease', '2.7'),
    'WFWorkflowMinimumClientVersion': base.get('WFWorkflowMinimumClientVersion', 900),
    'WFWorkflowMinimumClientVersionString': base.get('WFWorkflowMinimumClientVersionString', '900'),
    'WFWorkflowName': base.get('WFWorkflowName', '推送健康数据'),
    'WFWorkflowIcon': base.get('WFWorkflowIcon'),
    'WFWorkflowImportQuestions': base.get('WFWorkflowImportQuestions', []),
    'WFWorkflowInputContentItemClasses': [],
    'WFWorkflowTypes': ['NCWidget', 'WatchKit'],
}
try_sign('core_only', dump(core, '_v_core.plist'))
try_sign('core_bin', dump(core, '_v_core_bin.plist', binary=True))
print()

print('=== 7) 用 shortcuts python 库 round-trip ===')
try:
    from shortcuts import Shortcut
    sc = Shortcut.load(open(SRC, 'rb'))
    print('库加载成功, 动作数 =', len(sc.actions))
    with open('_rt.shortcut', 'wb') as f:
        sc.dump(f)
    try_sign('roundtrip', '_rt.shortcut')
except Exception as e:
    print('库处理失败:', type(e).__name__, str(e)[:120])
