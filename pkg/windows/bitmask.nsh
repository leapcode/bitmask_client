# pwd is a ro-mounted source-tree that had all dependencies build into
# package-name directories
!define PKGNAMEPATH ..\..\build\executables\${PKGNAME}
!include ${PKGNAMEPATH}_version.nsh
!include .\bitmask_client_product.nsh
!include ${PKGNAMEPATH}_install_files_size.nsh

RequestExecutionLevel admin ;Require admin rights on NT6+ (When UAC is turned on)

InstallDir "$PROGRAMFILES\${APPNAME}"

LicenseData "..\..\LICENSE"
Name "${COMPANYNAME} - ${APPNAME}"
Icon "..\..\build\executables\mask-icon.ico"

# /var/dist is a rw mounted volume
outFile "/var/dist/${PKGNAME}-${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}${VERSIONSUFFIX}.exe"
!include LogicLib.nsh

# Just three pages - license agreement, install location, and installation
page license
page directory
Page instfiles

!macro VerifyUserIsAdmin
UserInfo::GetAccountType
pop $0
${If} $0 != "admin" ;Require admin rights on NT4+
    messageBox mb_iconstop "Administrator rights required!"
    setErrorLevel 740 ;ERROR_ELEVATION_REQUIRED
    quit
${EndIf}
!macroend

function .onInit
    setShellVarContext all
    !insertmacro VerifyUserIsAdmin
functionEnd

section "TAP Virtual Ethernet Adapter" SecTAP
    SetOverwrite on
    SetOutPath "$TEMP"
    File /oname=tap-windows.exe "..\..\build\executables\openvpn\tap-windows.exe"

    DetailPrint "Installing TAP (may need confirmation)..."
    nsExec::ExecToLog '"$TEMP\tap-windows.exe" /S /SELECT_UTILITIES=1'
    Pop $R0 # return value/error/timeout

    Delete "$TEMP\tap-windows.exe"
    WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "tap" "installed"
sectionEnd

section "install"
    setOutPath $INSTDIR

    !include ${PKGNAMEPATH}_install_files.nsh

    # Uninstaller - See function un.onInit and section "uninstall" for configuration
    writeUninstaller "$INSTDIR\uninstall.exe"

    # Start Menu
    createDirectory "$SMPROGRAMS\${COMPANYNAME}"
    createShortCut "$SMPROGRAMS\${COMPANYNAME}\${APPNAME}.lnk" "$INSTDIR\bitmask.exe" "" "$INSTDIR\bitmask.exe"

    !include bitmask_client_registry_install.nsh
sectionEnd

# Uninstaller

function un.onInit
    SetShellVarContext all
    !insertmacro VerifyUserIsAdmin
functionEnd

section "uninstall"

    delete "$SMPROGRAMS\${COMPANYNAME}\${APPNAME}.lnk"
    # Try to remove the Start Menu folder - this will only happen if it is empty
    rmDir "$SMPROGRAMS\${COMPANYNAME}"

    # Remove files
    !include ${PKGNAMEPATH}_uninstall_files.nsh

    # Remove TAP Drivers
    ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "tap"
    ${If} $R0 == "installed"
        DetailPrint "Uninstalling TAP as we installed it..."
        ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TAP-Windows" "UninstallString"
        ${If} $R0 != ""
            DetailPrint "Uninstalling TAP..."
            nsExec::ExecToLog '"$R0" /S'
            Pop $R0 # return value/error/timeout
        ${Else}
            # on x64 windows the uninstall location needs to be accessed using WOW
            SetRegView 64
            ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TAP-Windows" "UninstallString"
            SetRegView 32
            ${If} $R0 != ""
                DetailPrint "Uninstalling TAP 64..."
                nsExec::ExecToLog '"$R0" /S'
                Pop $R0 # return value/error/timeout
            ${EndIf}
        ${EndIf}
        DeleteRegValue HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "tap"
    ${EndIf}

    # Always delete uninstaller as the last action
    delete $INSTDIR\uninstall.exe

    # Try to remove the install directory - this will only happen if it is empty
    rmDir $INSTDIR

    # Remove uninstaller information from the registry
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}"
sectionEnd