[Setup]
AppName=DriverScanner Pro
AppVersion=1.0.0
AppPublisher=DriverScanner Team
DefaultDirName={autopf}\DriverScanner Pro
DefaultGroupName=DriverScanner Pro
SetupIconFile=C:\DriverScanner\app_icon.ico
UninstallDisplayIcon={app}\DriverScanner.exe
OutputDir=C:\DriverScanner\installer
OutputBaseFilename=DriverScanner_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "C:\DriverScanner\dist\DriverScanner.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\DriverScanner Pro"; Filename: "{app}\DriverScanner.exe"
Name: "{group}\Удалить DriverScanner Pro"; Filename: "{uninstallexe}"
Name: "{autodesktop}\DriverScanner Pro"; Filename: "{app}\DriverScanner.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DriverScanner.exe"; Description: "Запустить DriverScanner Pro"; Flags: nowait postinstall skipifsilent
