; PBW3 Tool Inno Setup Script
#define MyAppName "PBW3 Tool"
#define MyAppExeName "PBW3 Tool v1.04.exe"
#define MyAppPublisher "PellDomPress"
#define MyAppVersion "1.04"
#define MyAppURL "https://www.pbw3.net/"
#define MyAppCopyright "Copyright (c) PellDomPress, Graphics: Mark Sedwick (Blackkynight) R.I.P."

[Setup]
AppId={{PBW3-TOOL-1234-5678}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppCopyright={#MyAppCopyright}
DefaultDirName={autopf}\PBW3 Tool
DefaultGroupName={#MyAppName}
OutputDir=dist
OutputBaseFilename=PBW3ToolSetup
SetupIconFile=Resources\PBW3.ico
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\PBW3 Tool v1.04.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Resources\*"; DestDir: "{app}\Resources"; Flags: ignoreversion recursesubdirs createallsubdirs

[Fonts]
Name: "SE4 Text Button"; Filename: "{app}\Resources\Fonts\SE4TXBTN.FON"; FontInstall: "SE4 Text Button"
Name: "Futurist Medium"; Filename: "{app}\Resources\Fonts\FutMed.fon"; FontInstall: "Futurist Medium"
Name: "SE4 Block 1 Small"; Filename: "{app}\Resources\Fonts\SE4BLK1S.FON"; FontInstall: "SE4 Block 1 Small"
Name: "SE4 Block 1 Medium"; Filename: "{app}\Resources\Fonts\SE4BLK1M.FON"; FontInstall: "SE4 Block 1 Medium"
Name: "SE4 Block 1 Large"; Filename: "{app}\Resources\Fonts\SE4BLK1L.FON"; FontInstall: "SE4 Block 1 Large"
Name: "Futurist Small"; Filename: "{app}\Resources\Fonts\FutSml.fon"; FontInstall: "Futurist Small"

[Icons]
Name: "{group}\PBW3 Tool"; Filename: "{app}\PBW3 Tool v1.04.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Resources\PBW3.ico"
Name: "{commondesktop}\PBW3 Tool"; Filename: "{app}\PBW3 Tool v1.04.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Resources\PBW3.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\PBW3 Tool v1.04.exe"; Description: "Launch PBW3 Tool"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\Resources"
Type: filesandordirs; Name: "{app}\.local-browsers" 