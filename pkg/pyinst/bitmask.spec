# -*- mode: python -*-

block_cipher = None


a = Analysis([os.path.join('pkg', 'pyinst', 'bitmask.py')],
             hiddenimports=[
	     	'zope.interface', 'zope.proxy',
		'PySide.QtCore', 'PySide.QtGui'],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)
pyz = PYZ(a.pure,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='bitmask',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='bitmask')
if sys.platform.startswith("darwin"):
	app = BUNDLE(coll,
		     name=os.path.join(
		      'dist', 'Bitmask.app'),
                     appname='Bitmask',
                     version='0.9.0rc2',
		     icon='pkg/osx/bitmask.icns',
		     bundle_identifier='bitmask-0.9.0rc2')
