#define AppVersion "0.1.0"

[Setup]
AppId={{33E39454-33BB-4E4C-8559-4403D2646E43}
AppName=RefCalendar
AppVersion={#AppVersion}
AppPublisher=Oscar Lohse
DefaultDirName={localappdata}\Programs\RefCalendar
DefaultGroupName=RefCalendar
UninstallDisplayIcon={app}\RefCalendar.exe
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist\installer
OutputBaseFilename=RefCalendar-Setup-{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Desktopverknüpfung erstellen"; GroupDescription: "Zusätzliche Verknüpfungen:"

[Files]
Source: "dist\RefCalendar\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\RefCalendar"; Filename: "{app}\RefCalendar.exe"
Name: "{autodesktop}\RefCalendar"; Filename: "{app}\RefCalendar.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RefCalendar.exe"; Description: "RefCalendar starten"; Flags: nowait postinstall skipifsilent
