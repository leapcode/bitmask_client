# -*- mode: python -*-
a = Analysis(['../../src/leap/app.py'], 
             pathex=[
		'../../src/leap',
		'/Users/kaliy/leap/leap_client/src/leap-client/pkg/osx'],
             hiddenimports=['atexit', 'leap.common'],
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
               a.binaries +
	       # this will easitly break if we setup the venv
	       # somewhere else. FIXME
	       [('cacert.pem', '/Users/kaliy/.Virtualenvs/leap-client/lib/python2.6/site-packages/requests-1.1.0-py2.6.egg/requests/cacert.pem', 'DATA'),
		],
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
