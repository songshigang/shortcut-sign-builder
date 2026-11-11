# -*- coding: utf-8 -*-
"""解决 shortcuts sign 的 NSUUID 类型问题。

macOS 的 plist 解析器把 UUID 字段当作 NSUUID（plist XML 里表示为 <string> 但带
T@ 标记，或用 UID 类型）。plistlib 写不出 UUID 对象，但可以：
  方案1：把 UUID 值写成 <data> 形式的 16 字节二进制（NSUUID 的真实存储形式）
  方案2：完全手写 XML plist 模板，精确控制每个节点的类型
本脚本先验证方案1。
"""
import plistlib, subprocess, os, uuid as uuidlib, struct

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
    msg = msg[0][:90] if msg else ''
    print(f'[{"OK  " if ok else "FAIL"}] {name:28s} {msg}')
    return ok


def uuid_bytes(u):
    """UUID → 16 字节 big-endian（NSUUID 的存储形式）。"""
    return u.bytes


def mk(path, uuid_as_data=False):
    u = uuidlib.uuid4()
    uval = uuid_bytes(u) if uuid_as_data else str(u).upper()
    d = {
        'WFWorkflowActions': [{
            'WFWorkflowActionIdentifier': 'is.workflow.actions.comment',
            'WFWorkflowActionParameters': {'WFCommentActionText': 'hi', 'UUID': uval},
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
        plistlib.dump(d, f, fmt=plistlib.FMT_XML)
    return path


print('=== UUID 作为 <data> 16字节（NSUUID 真实形式）===')
sign(mk('_d.plist', uuid_as_data=True), 'uuid_as_data')
print()

print('=== 手写 XML plist（精确控制类型）===')
XML = '''<?xml version="1.0" encoding="UTF-8"?>
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
        <key>UUID</key>
        <string>8F2A1B3C-4D5E-6F70-8192-A3B4C5D6E7F8</string>
      </dict>
    </dict>
  </array>
  <key>WFWorkflowClientVersion</key>
  <string>2607.0.3</string>
  <key>WFWorkflowClientRelease</key>
  <string>2.7</string>
  <key>WFWorkflowMinimumClientVersion</key>
  <integer>900</integer>
  <key>WFWorkflowMinimumClientVersionString</key>
  <string>900</string>
  <key>WFWorkflowName</key>
  <string>test</string>
  <key>WFWorkflowIcon</key>
  <dict>
    <key>WFWorkflowIconGlyphNumber</key>
    <integer>59511</integer>
    <key>WFWorkflowIconStartColor</key>
    <integer>4282601983</integer>
  </dict>
  <key>WFWorkflowImportQuestions</key>
  <array/>
  <key>WFWorkflowInputContentItemClasses</key>
  <array/>
  <key>WFWorkflowTypes</key>
  <array>
    <string>NCWidget</string>
    <string>WatchKit</string>
  </array>
</dict>
</plist>
'''
open('_x.plist', 'w', encoding='utf-8').write(XML)
sign('_x.plist', 'handwritten_xml')

print()
print('=== 关键对照：plutil 转成 binary 再签 ===')
run(['plutil', '-convert', 'binary1', '_x.plist', '-o', '_x.bin'])
if os.path.exists('_x.bin'):
    sign('_x.bin', 'handwritten_bin')
print()
print('=== shortcuts view 能否打开（另一种校验）===')
rc, so, se = run(['shortcuts', 'view', '_x.plist'])
print('view rc=', rc, (se or so)[:160])
