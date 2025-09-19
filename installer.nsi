; installer.nsi
; NSIS installer for MDI AutoLogin
!include "MUI2.nsh"

!define PRODUCT_NAME "MDI AutoLogin"
!define PRODUCT_EXE  "mdi_autologin.exe"
!define COMPANY_NAME "MDI Project"
!define INSTALL_DIR  "$PROGRAMFILES\${PRODUCT_NAME}"
!define RUN_REG_KEY  "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
!define RUN_VALUE_NAME "${PRODUCT_NAME}"

Name "${PRODUCT_NAME}"
OutFile "mdi_autologin_installer.exe"
InstallDir "${INSTALL_DIR}"
RequestExecutionLevel user    ; HKCU writes do not require admin

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY

; Custom page with 'Run at startup' checkbox
Page custom StartupOptionsPage StartupOptionsLeave

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Var STARTUP_CHECK

; ---------- Functions for the custom page ----------
Function StartupOptionsPage
  !insertmacro MUI_HEADER_TEXT "Installation options" "Choose install options"
  ; create controls
  GetDlgItem $R0 $HWNDPARENT 1 ; not used, just to ensure $R0 exists
  ; default checked
  StrCpy $STARTUP_CHECK "1"
  ; Create the checkbox (left, top, width, height)
  ${NSD_CreateCheckBox} 20 40 200 12 "Run ${PRODUCT_NAME} at Windows startup"
  Pop $R0
  ${NSD_SetState} $R0 ${BST_CHECKED}
  ; save handle to stack for read later
  Push $R0
FunctionEnd

Function StartupOptionsLeave
  ; pop handle and read state
  Pop $R0
  ${NSD_GetState} $R0 $R1
  StrCmp $R1 ${BST_CHECKED} 0 +3
    StrCpy $STARTUP_CHECK "1"
    Goto done
  StrCpy $STARTUP_CHECK "0"
  done:
FunctionEnd

; ---------- Installer ----------
Section "Install"
  SetOutPath "$INSTDIR"
  ; Ensure dist exe path exists - user should run makensis from repo root
  File /oname=${PRODUCT_EXE} "dist\${PRODUCT_EXE}"

  ; create desktop shortcut
  CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\${PRODUCT_EXE}"

  ; start menu shortcut
  CreateDirectory "$SMPROGRAMS\${COMPANY_NAME}\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${COMPANY_NAME}\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\${PRODUCT_EXE}"

  ; If the user opted to enable startup, write HKCU\Run (no admin needed)
  StrCmp $STARTUP_CHECK "1" 0 +3
    WriteRegStr HKCU "${RUN_REG_KEY}" "${RUN_VALUE_NAME}" '"$INSTDIR\${PRODUCT_EXE}"'
  ; Create uninstall entry (basic)
  WriteUninstaller "$INSTDIR\Uninstall.exe"

SectionEnd

; ---------- Uninstaller ----------
Section "Uninstall"
  ; remove shortcuts
  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${COMPANY_NAME}\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk"
  RMDir "$SMPROGRAMS\${COMPANY_NAME}\${PRODUCT_NAME}"

  ; remove exe and installer files
  Delete "$INSTDIR\${PRODUCT_EXE}"
  Delete "$INSTDIR\Uninstall.exe"

  ; remove registry run value if present
  DeleteRegValue HKCU "${RUN_REG_KEY}" "${RUN_VALUE_NAME}"

  ; remove install dir (silent fail if not empty)
  RMDir "$INSTDIR"

SectionEnd
