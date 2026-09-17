#define MyAppName "NEXO"
#define MyAppVersion "1.1.0-preview"
#define MyAppPublisher "NEXO"
#define MyAppExeName "NEXO.exe"

[Setup]
AppId={{4D69D6DF-8A0C-4FCE-96AA-77C3B4C81211}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\NEXO
DefaultGroupName=NEXO
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=NEXO-Setup
SetupIconFile=..\src\windows\MacroPadRemote\Nexo.ico
UninstallDisplayName=NEXO
UninstallDisplayIcon={app}\NEXO.exe
UninstallFilesDir={app}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
SetupLogging=yes
VersionInfoVersion=1.1.0.0
VersionInfoProductName=NEXO Setup
VersionInfoProductVersion=1.1.0.0
VersionInfoCompany=NEXO
VersionInfoDescription=NEXO Setup

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык NEXO на рабочем столе"; GroupDescription: "Дополнительные параметры:"; Flags: checkedonce

[Files]
Source: "..\dist\windows\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\NEXO"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{app}\NEXO-Uninstall"; Filename: "{uninstallexe}"; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить NEXO"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
const
  NexoBg = $001B1917;
  NexoPanel = $00211F1D;
  NexoText = $00F2F2F2;
  NexoMuted = $00A8A39D;

procedure InitializeWizard;
begin
  WizardForm.Color := NexoBg;
  WizardForm.MainPanel.Color := NexoPanel;
  WizardForm.InnerPage.Color := NexoBg;
  WizardForm.WelcomeLabel1.Font.Color := NexoText;
  WizardForm.WelcomeLabel2.Font.Color := NexoMuted;
  WizardForm.PageNameLabel.Font.Color := NexoText;
  WizardForm.PageDescriptionLabel.Font.Color := NexoMuted;
  WizardForm.NextButton.Caption := 'Далее';
  WizardForm.BackButton.Caption := 'Назад';
  WizardForm.CancelButton.Caption := 'Отмена';
end;
