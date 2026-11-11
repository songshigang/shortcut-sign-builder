# -*- coding: utf-8 -*-
"""终极验证：让 macOS 自己生成 plist，再签。若仍失败 → CLI 在 runner 上不可用。"""
import subprocess, os, shutil

OUT = '_signout'
os.makedirs(OUT, exist_ok=True)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()


def show(tag, rc, msg):
    m = (msg or '').strip().splitlines()
    m = m[0][:100] if m else ''
    print(f'  {tag}: rc={rc} {m}')


print('=== 1) plutil 造一个最简单的 plist（macOS 自己的工具）===')
with open('_p.plist', 'w', encoding='utf-8') as f:
    f.write('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>WFWorkflowActions</key>
  <array>
    <dict>
      <key>WFWorkflowActionIdentifier</key>
      <string>is.workflow.actions.comment</string>
      <key>WFWorkflowActionParameters</key>
      <dict>
        <key>WFCommentActionText</key>
        <string>hi</string>
      </dict>
    </dict>
  </array>
  <key>WFWorkflowClientVersion</key>
  <string>2607.0.3</string>
  <key>WFWorkflowInputContentItemClasses</key>
  <array/>
</dict>
</plist>
''')

rc, so, se = run(['plutil', '-lint', '_p.plist'])
show('plutil lint', rc, so or se)

print()
print('=== 2) 直接签 .plist（不 cp）===')
rc, so, se = run(['shortcuts', 'sign', '-i', '_p.plist', '-o', '_p1.shortcut',
                   '-m', 'anyone', '-m', 'anyone'])
show('sign .plist', rc, se or so)

print()
print('=== 3) cp 成 .shortcut 再签 ===')
shutil.copyfile('_p.plist', '_p.shortcut')
rc, so, se = run(['shortcuts', 'sign', '-i', '_p.shortcut', '-o', '_p2.shortcut',
                   '-m', 'anyone', '-m', 'anyone'])
show('sign .shortcut', rc, se or so)

print()
print('=== 4) defaults 写一个 plist 再签（系统级工具生成）===')
run(['/usr/libexec/PlistBuddy', '-c', 'Add :WFWorkflowActions:0:WFWorkflowActionIdentifier string is.workflow.actions.comment',
     '_p.plist'])
run(['/usr/libexec/PlistBuddy', '-c', 'Add :WFWorkflowClientVersion string 2607.0.3', '_p.plist'])
rc, so, se = run(['plutil', '-convert', 'binary1', '_p.plist', '-o', '_pb.plist'])
show('plistbuddy+convert', rc, se or so)
shutil.copyfile('_pb.plist', '_pb.shortcut')
rc, so, se = run(['shortcuts', 'sign', '-i', '_pb.shortcut', '-o', '_p3.shortcut',
                   '-m', 'anyone', '-m', 'anyone'])
show('sign plistbuddy', rc, se or so)

print()
print('=== 5) 环境检查：Shortcuts.app / 是否有 GUI 会话 ===')
for c in (['ls', '-d', '/Applications/Shortcuts.app'],
          ['launchctl', 'print', 'gui/501'],
          ['defaults', 'read', 'com.apple.shortcuts']):
    rc, so, se = run(c)
    print(f'  $ {" ".join(c[:2])} → rc={rc}')
    if so: print('   ', so[:180])
    if se and not so: print('   err:', se[:180])

print()
print('=== 6) 是否已有产物 ===')
for f in sorted(os.listdir(OUT)):
    print('  ', f, os.path.getsize(os.path.join(OUT, f)))
