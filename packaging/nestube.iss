; Inno Setup script — NesTube Windows installer
; Build after PyInstaller: packaging\build_installer.ps1

#define MyAppName "NesTube"
; Version is passed in by the build scripts via /DMyAppVersion=<ver> so the
; installer filename always matches nestube.__version__. The fallback below is
; only used for ad-hoc local builds that invoke ISCC without that flag.
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0-pre-alpha.1"
#endif
#define MyAppPublisher "Alberto Miranda"
#define MyAppURL "https://github.com/Grohle/nestube"
#define MyAppExeName "NesTube.exe"

[Setup]
AppId={{A8F3C2E1-9B4D-4F6A-8C1E-1000A1FA0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=..
OutputBaseFilename=NesTube-{#MyAppVersion}-setup
SetupIconFile=..\nestube\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\NesTube\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
