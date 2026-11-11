# -*- coding: utf-8 -*-
"""深挖 shortcuts sign 失败的真实原因。"""
import plistlib, subprocess, os, plistlib as pl

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()

print('=== 1) CLI 帮助 ===')
for c in (['shortcuts'], ['shortcuts', 'sign', '--help'], ['shortcuts', '-h']):
    rc, out, err = run(c)
    print(f'$ {" ".join(c)}  → rc={rc}')
    print((out or err)[:700])
    print('-' * 50)

print()
print('=== 2) 造一个标准样式的最小 plist（含 WFWorkflowClientRelease 等）===')
mini = {
    'WFWorkflowActions': [{
        'WFWorkflowActionIdentifier': 'is.workflow.actions.comment',
        'WFWorkflowActionParameters': {'WFCommentActionText': 'hi'},
    }],
    'WFWorkflowClientVersion': '2607.0.3',
    'WFWorkflowClientRelease': '2.7',
    'WFWorkflowMinimumClientVersion': 900,
    'WFWorkflowMinimumClientVersionString': '900',
    'WFWorkflowName': 'test',
    'WFWorkflowInputContentItemClasses': [],
    'WFWorkflowTypes': [],
}
with open('_m.plist', 'wb') as f:
    pl.dump(mini, f, fmt=pl.FMT_XML)

for args in (
    ['shortcuts', 'sign', '-i', '_m.plist', '-o', '_m.shortcut', '-m', 'anyone', '-m', 'anyone'],
    ['shortcuts', 'sign', '-i', '_m.plist', '-o', '_m.shortcut', '-m', 'anyone'],
    ['shortcuts', 'sign', '-i', '_m.plist', '-o', '_m.shortcut'],
):
    rc, out, err = run(args)
    print(f'$ {" ".join(args[1:])}')
    print(f'  rc={rc}  exists={os.path.exists("_m.shortcut")}')
    if out: print('  out:', out[:200])
    if err: print('  err:', err[:200])
    if os.path.exists('_m.shortcut'):
        os.remove('_m.shortcut')
    print('-' * 40)

print()
print('=== 3) 系统信息 ===')
rc, out, err = run(['sw_vers'])
print(out or err)
rc, out, err = run(['uname', '-m'])
print('arch:', out)

print()
print('=== 4) 是否有 Xcode / 图形上下文 ===')
rc, out, err = run(['ls', '/Applications/Shortcuts.app'])
print('Shortcuts.app:', out or err or '(缺失)')

print()
print('=== 5) 尝试 shortcut-sign（跨平台）===')
rc, out, err = run(['shortcut-sign', 'version'])
print('shortcut-sign:', rc, out[:120], err[:120])
