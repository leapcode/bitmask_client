
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
daemon_a = Analysis(['bitmaskd'],
             binaries=None,
             datas=None,
             hiddenimports=[
	     	'leap.bitmask.core.service'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

MERGE( (gui_a, 'bitmask', 'bitmask'),
       (cli_a, 'bitmask_cli', 'bitmask'),
       (daemon_a, 'bitmaskd', 'bitmaskd'))

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
daemon_pyz = PYZ(daemon_a.pure, daemon_a.zipped_data, cipher=block_cipher)
daemon_exe = EXE(daemon_pyz,
          daemon_a.scripts,
          exclude_binaries=True,
          name='bitmaskd', debug=False, strip=False, upx=True, console=True )

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
daemon_coll = COLLECT(daemon_exe,
               daemon_a.binaries,
               daemon_a.zipfiles,
               daemon_a.datas,
               strip=False, upx=True, name='bitmaskd')
