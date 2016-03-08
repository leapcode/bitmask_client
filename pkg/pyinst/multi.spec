
# -*- mode: python -*-

block_cipher = None


gui_a = Analysis(['bitmask.py'],
             hiddenimports=[
	     	'zope.interface', 'zope.proxy',
		'PySide.QtCore', 'PySide.QtGui'],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)
cli_a = Analysis(['bitmask_cli'],
             pathex=['/home/kali/leap/bitmask_client/pkg/pyinst'],
             binaries=None,
             datas=None,
             hiddenimports=[
	     	'zope.interface', 'zope.proxy'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

MERGE( (gui_a, 'bitmask', 'bitmask'),
       (cli_a, 'bitmask_cli', 'bitmask'))

gui_pyz = PYZ(gui_a.pure, gui_a.zipped_data, cipher=block_cipher)
gui_exe = EXE(gui_pyz,
          gui_a.scripts,
          exclude_binaries=True,
          name='bitmask', debug=False, strip=False,
          upx=True, console=False )

cli_pyz = PYZ(cli_a.pure, cli_a.zipped_data, cipher=block_cipher)
cli_exe = EXE(cli_pyz,
          cli_a.scripts,
          exclude_binaries=True,
          name='bitmask_cli', debug=False, strip=False,
          upx=True, console=True)

gui_coll = COLLECT(gui_exe,
               gui_a.binaries,
               gui_a.zipfiles,
               gui_a.datas,
               strip=False, upx=True, name='bitmask')
cli_coll = COLLECT(cli_exe,
               cli_a.binaries,
               cli_a.zipfiles,
               cli_a.datas,
               strip=False, upx=True, name='bitmask_cli')
