# -*- coding: utf-8 -*-
"""矩阵测试：找出 shortcuts sign 能接受的输入形态。"""
import plistlib, subprocess, os, itertools, sys

OUTDIR = '_signout'
os.makedirs(OUTDIR, exist_ok=True)

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()

def make_plist(path, actions, binary=False, extra=None):
    d = {
        'WFWorkflowActions': actions,
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
    if extra:
        d.update(extra)
    with open(path, 'wb') as f:
        plistlib.dump(d, f, fmt=plistlib.FMT_BINARY if binary else plistlib.FMT_XML)
    return path

COMMENT_ACTION = [{
    'WFWorkflowActionIdentifier': 'is.workflow.actions.comment',
    'WFWorkflowActionParameters': {'WFCommentActionText': 'hi'},
}]

results = []

def trial(name, infile):
    out = os.path.join(OUTDIR, name + '.shortcut')
    if os.path.exists(out):
        os.remove(out)
    rc, so, se = run(['shortcuts', 'sign', '-i', infile, '-o', out,
                       '-m', 'anyone', '-m', 'anyone'])
    ok = os.path.exists(out) and os.path.getsize(out) > 0
    msg = (se or so or '').strip().splitlines()
    msg = msg[0][:70] if msg else ''
    results.append((name, ok, msg))
    print(f'[{"OK  " if ok else "FAIL"}] {name:34s} {msg}')
    return ok

print('=== A) 扩展名矩阵 ===')
for ext in ('.plist', '.shortcut'):
    for binary in (False, True):
        p = make_plist(f'_a{ext}', COMMENT_ACTION, binary=binary)
        trial(f'ext{ext}_bin{int(binary)}', p)

print()
print('=== B) 从真实快捷指令库导出的结构（带 WFWorkflowTypes 空 + HasOutputFallback）===')
p = make_plist('_b.plist', COMMENT_ACTION, extra={
    'WFWorkflowHasOutputFallback': True,
    'WFWorkflowHasShortcutInputVariables': False,
    'WFWorkflowOutputContentItemClasses': [],
})
trial('with_fallback', p)

print()
print('=== C) 尝试 shortcuts list 看环境 ===')
rc, so, se = run(['shortcuts', 'list'])
print('list rc=', rc, (so or se)[:200])

print()
print('=== 汇总 ===')
for n, ok, m in results:
    print(f'  {"✓" if ok else "✗"} {n}  {m}')
print()
print('成功数:', sum(1 for _, ok, _ in results if ok), '/', len(results))
