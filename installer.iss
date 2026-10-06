; AXUS GROUP — Treolan Manager
#define MyAppName "AXUS Treolan Manager"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AXUS GROUP"
#define MyAppExeName "AXUS-Treolan-Manager.exe"

[Setup]
AppId={{A9A6B6D0-0B1A-4B75-9E5C-AXUS2026TREOLAN}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AXUS GROUP\Treolan Manager
DefaultGroupName=AXUS GROUP\Treolan Manager
OutputDir=..\installer
OutputBaseFilename=AXUS-Treolan-Manager-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\AXUS-Treolan-Manager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\data.xlsx"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\seed_catalog.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\axus_logo.jpg"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить AXUS Treolan Manager"; Flags: nowait postinstall skipifsilent
