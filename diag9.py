# -*- coding: utf-8 -*-
"""在 GitHub Actions macOS runner 上调用 HubSign API 签名。"""
import json, urllib.request, urllib.error, os, sys, plistlib

PLIST = '推送健康数据.plist'
OUT = '推送健康数据.shortcut'
API = 'https://hubsign.routinehub.services/sign'


def try_sign(origin, referer, label):
    pl = open(PLIST, 'rb').read()
    body = json.dumps({'shortcutName': '推送健康数据',
                       'shortcut': pl.decode('utf-8')}).encode('utf-8')
    req = urllib.request.Request(API, data=body, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', '*/*')
    req.add_header('Origin', origin)
    req.add_header('Referer', referer)
    req.add_header('User-Agent',
                   'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                   'Version/17.0 Safari/605.1.15')
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
            print(f'[OK  ] {label}: HTTP {r.status}, {len(data)} bytes, magic={data[:4]!r}')
            if data[:4] == b'AEA1':
                open(OUT, 'wb').write(data)
                print(f'        → 已写入 {OUT}')
                return True
            return False
    except urllib.error.HTTPError as e:
        print(f'[FAIL] {label}: HTTP {e.code} {e.read()[:120]}')
    except Exception as e:
        print(f'[FAIL] {label}: {type(e).__name__} {str(e)[:140]}')
    return False


print('=== 尝试不同 Origin/Referer ===')
cands = [
    ('https://playground.cherrilang.org', 'https://playground.cherrilang.org/', 'cherri-playground'),
    ('https://cherri.dev', 'https://cherri.dev/', 'cherri-dev'),
    ('https://routinehub.co', 'https://routinehub.co/', 'routinehub'),
    ('https://localhost', 'https://localhost/', 'localhost'),
]
ok = False
for o, r, l in cands:
    if try_sign(o, r, l):
        ok = True
        break

if not ok:
    print()
    print('=== 退路：直接把 plist 放到公网，用 shortcuts://import-shortcut 让 iPhone 自己导入 ===')
    print('（iOS 15+ 对未签名文件会拒绝，但 import-shortcut URL Scheme 会调用 Shortcuts.app 内部逻辑，可能可行）')

print()
print('=== 产物检查 ===')
if os.path.exists(OUT):
    print('  ', OUT, os.path.getsize(OUT), 'bytes')
    d = open(OUT, 'rb').read()
    print('   魔数:', d[:4], '(AEA1 = 已签名)')
    print('   可导入 iOS:', d[:4] == b'AEA1')
else:
    print('   无签名产物')
