!include "MUI2.nsh"

; Web Whisper Portable NSIS script
; - Extracts to %TEMP% and runs without installation
; - Packs Tauri frontend exe and Python sidecar exe

Name "Web Whisper Portable"
OutFile "${OutFile}"
RequestExecutionLevel user
Unicode true
SetCompress auto
SetCompressor /SOLID lzma

!define APP_NAME "Web Whisper"
!define STAGE_DIR "stage"
!define TEMP_DIR "$TEMP\\WebWhisperPortable"

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Japanese"

Section "Portable"
  SetOutPath "${TEMP_DIR}"

  ; Required app files (prepared beforehand under windows-release/stage)
  File /r "${STAGE_DIR}\\*.*"

  ; Optional: WebView2 fixed runtime support
  ; If you place a folder `WebView2Runtime` under stage, set env var to use it.
  ${If} ${FileExists} "${TEMP_DIR}\\WebView2Runtime\\msedgewebview2.exe"
    StrCpy $1 "${TEMP_DIR}\\WebView2Runtime"
    System::Call 'Kernel32::SetEnvironmentVariableW(w "WEBVIEW2_BROWSER_EXECUTABLE_FOLDER", w r1) i .r0'
  ${EndIf}

  ; Launch app and wait; try common exe names
  ; Prefer release exe name as built by Tauri (productName)
  StrCpy $0 "${TEMP_DIR}\\Web Whisper.exe"
  ${IfNot} ${FileExists} "$0"
    StrCpy $0 "${TEMP_DIR}\\web-whisper.exe"
  ${EndIf}

  ${If} ${FileExists} "$0"
    ExecWait '"$0"'
  ${Else}
    MessageBox MB_ICONSTOP "App executable not found in portable package."
  ${EndIf}

  ; Cleanup extracted files on exit
  RMDir /r "${TEMP_DIR}"
SectionEnd
