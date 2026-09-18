from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def main() -> None:
    cs_path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml.cs"
    text = cs_path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''    private void AddProfile_Click(object sender, RoutedEventArgs e)
    {
        var name = Prompt("Новый профиль", $"Профиль {_profiles.Count + 1}");
        if (name is null) return;
        var profile = DefaultProfile(name, name[..1].ToUpperInvariant());
        _profiles.Add(profile); _state.ActiveProfileId = profile.Id; SaveState(); RefreshProfiles();
    }''',
        '''    private void AddProfile_Click(object sender, RoutedEventArgs e)
    {
        var name = V141PromptNewProfileName(this);
        if (name is null) return;
        var profile = DefaultProfile(name, name[..1].ToUpperInvariant());
        _profiles.Add(profile);
        _state.ActiveProfileId = profile.Id;
        SaveState();
        RefreshProfiles();
        ProfileBox.SelectedItem = profile;
        _ = BroadcastSnapshotAsync();
    }''',
        "require profile name",
    )

    text = replace_once(
        text,
        '''    public DateTime DeviceLinkUpdatedUtc { get; set; } = DateTime.MinValue;
    public string SourceServerId { get; set; } = "";''',
        '''    public DateTime DeviceLinkUpdatedUtc { get; set; } = DateTime.MinValue;
    public List<V141LinkedDevice> LinkedDevices { get; set; } = new();
    public DateTime ProfileWorkspaceUpdatedUtc { get; set; } = DateTime.MinValue;
    public string ProfileWorkspaceHash { get; set; } = "";
    public string SourceServerId { get; set; } = "";''',
        "linked devices and profile revision state",
    )

    text = replace_once(
        text,
        '''        _state.WorkspaceUpdatedUtc = DateTime.UtcNow;
        try
        {
            V14PersistProfilesToProgramFolder();''',
        '''        _state.WorkspaceUpdatedUtc = DateTime.UtcNow;
        V141UpdateProfileRevision();
        try
        {
            V14PersistProfilesToProgramFolder();''',
        "update profile revision on save",
    )

    cs_path.write_text(text, encoding="utf-8")

    xaml_path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml"
    xaml = xaml_path.read_text(encoding="utf-8")

    xaml = replace_once(
        xaml,
        '''        <Grid.ColumnDefinitions>
            <ColumnDefinition Width="0"/>
            <ColumnDefinition Width="*"/>
            <ColumnDefinition Width="385"/>
        </Grid.ColumnDefinitions>''',
        '''        <Grid.ColumnDefinitions>
            <ColumnDefinition Width="285"/>
            <ColumnDefinition Width="*"/>
            <ColumnDefinition Width="385"/>
        </Grid.ColumnDefinitions>''',
        "restore profile selector column",
    )

    xaml = xaml.replace(
        '<Button Grid.Column="1" Content="＋" Width="34" Height="30" Click="AddProfile_Click"/>',
        '<Button Grid.Column="1" Content="＋" Width="34" Height="30" Click="AddProfile_Click" Visibility="Collapsed"/>',
        1,
    )
    xaml = xaml.replace(
        '<Grid.ColumnDefinitions><ColumnDefinition Width="50"/><ColumnDefinition/><ColumnDefinition Width="38"/></Grid.ColumnDefinitions>',
        '<Grid.ColumnDefinitions><ColumnDefinition Width="50"/><ColumnDefinition/><ColumnDefinition Width="0"/></Grid.ColumnDefinitions>',
        1,
    )
    xaml = xaml.replace(
        '<Button x:Name="ProfileDots" Grid.Column="2" Content="⋮" FontSize="20" Background="Transparent" BorderThickness="0" Visibility="Hidden" Tag="{Binding}" Click="ProfileMenu_Click"/>',
        '<Button x:Name="ProfileDots" Grid.Column="2" Content="⋮" FontSize="20" Background="Transparent" BorderThickness="0" Visibility="Collapsed" Tag="{Binding}" Click="ProfileMenu_Click"/>',
        1,
    )
    xaml = xaml.replace(
        '<Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition Width="40"/></Grid.ColumnDefinitions>\n                        <Button Content="＋  Добавить профиль" HorizontalContentAlignment="Left" Click="AddProfile_Click"/>\n                        <Button Grid.Column="1" Content="−" Margin="6,0,0,0" Click="DeleteProfile_Click"/>',
        '<Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition Width="0"/></Grid.ColumnDefinitions>\n                        <Button Content="＋  Добавить профиль" HorizontalContentAlignment="Left" Click="AddProfile_Click"/>\n                        <Button Grid.Column="1" Content="−" Margin="6,0,0,0" Click="DeleteProfile_Click" Visibility="Collapsed"/>',
        1,
    )
    xaml = xaml.replace('Text="  v1.4.0 preview"', 'Text="  v1.4.1 preview"', 1)
    xaml_path.write_text(xaml, encoding="utf-8")

    print(f"Applied NEXO v1.4.1 Windows UI fixes: {cs_path}")


if __name__ == "__main__":
    main()
