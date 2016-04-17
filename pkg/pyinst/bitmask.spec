# -*- mode: python -*-
import sys

block_cipher = None

# TODO remove QtWebKit for bundles that don't ship pixelated???
a = Analysis(['bitmask.py'],
             hiddenimports=[
               'zope.interface', 'zope.proxy',
               'PySide.QtCore', 'PySide.QtGui', 'PySide.QtWebKit',
               'pysqlcipher', 'service_identity',
               'leap.common', 'leap.bitmask'
               ],
             binaries=None,
             datas=None,
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

# Binary files you need to include in the form of:
# (<destination>, <source>, '<TYPE>')

# Data files you want to include, in the form of:
# (<destination>, <source>, '<TYPE>')
data = [
  ('qt.conf', 'qt.conf', 'DATA')
]
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='bitmask',
          debug=True,
          strip=None,
          upx=True,
          console=False,
          icon='../../data/images/mask-icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='bitmask')
if sys.platform.startswith("darwin"):
	app = BUNDLE(coll,
		     name=os.path.join(
		      'dist', 'Bitmask.app'),
                     appname='Bitmask',
                     version='0.9.0.alpha7',
		     icon='pkg/osx/bitmask.icns',
		     bundle_identifier='bitmask-0.9.0alpha7')
