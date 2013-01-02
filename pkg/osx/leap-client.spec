# -*- mode: python -*-
a = Analysis(['../../src/leap/app.py'], 
             pathex=[
		'../../src/leap',
		'/Users/kaliy/leap/leap-client-testbuild/src/leap-client/pkg/osx'],
             hiddenimports=['atexit'],
             hookspath=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build/pyi.darwin/leap-client', 'app'),
          debug=False,
          strip=True,
          upx=True,
          console=False)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=True,
               upx=True,
               name=os.path.join('dist', 'app'))
app = BUNDLE(coll,
             name=os.path.join('dist', 'leap-client.app'))

import sys
if sys.platform.startswith("darwin"):
    app = BUNDLE(coll,
		 name=os.path.join('dist', 'LEAP Client.app'),
                 appname='LEAP Client',
                 version=1)
