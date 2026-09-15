using System.Collections.ObjectModel;
using System.IO;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Net.WebSockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Hosting;

namespace MacroPadRemote;

public partial class MainWindow : Window
{
    readonly string dataDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "MacroPadRemote");
    readonly ObservableCollection<Profile> profiles = new();
    readonly List<WebSocket> clients = new();
    Profile? current; Tile? selectedTile; WebApplication? server;
    string pairCode = "";

    public MainWindow()
    {
        InitializeComponent(); Directory.CreateDirectory(dataDir); Load();
        ProfilesList.ItemsSource = profiles; ProfilesList.SelectedIndex = 0;
        ActionsList.ItemsSource = KeyActions(); AddressText.Text = $"Wi-Fi: {LocalIp()}:8765";
    }

    void Load()
    {
        try { var p = JsonSerializer.Deserialize<List<Profile>>(File.ReadAllText(Path.Combine(dataDir,"presets.json"))); if (p != null) foreach(var x in p) profiles.Add(x); } catch { }
        if (profiles.Count == 0) { profiles.Add(Default("Revit","R")); profiles.Add(Default("NanoCAD","N")); profiles.Add(Default("Рабочий стол","▣")); }
    }
    Profile Default(string name,string icon)
    {
        var p=new Profile{Name=name,Icon=icon,Rows=3,Columns=4};
        string[] n={"Сохранить","Скриншот","Переключить окна","Браузер","Назад","Воспроизведение","Выключить звук","Рабочий стол","Почта","Калькулятор","Открыть папку","Добавить"};
        string[] h={"CTRL+S","WIN+SHIFT+S","ALT+TAB","CTRL+L","ESC","MEDIA_PLAY","VOLUME_MUTE","WIN+D","","","",""};
        for(int i=0;i<n.Length;i++)p.Tiles.Add(new Tile{Title=n[i],Hotkey=h[i]}); return p;
    }
    void SaveLocal(){ if(current!=null){current.Name=ProfileNameBox.Text.Trim();current.Description=DescriptionBox.Text;current.Rows=Num(RowsBox.Text,1,8);current.Columns=Num(ColumnsBox.Text,1,10);} File.WriteAllText(Path.Combine(dataDir,"presets.json"),JsonSerializer.Serialize(profiles,new JsonSerializerOptions{WriteIndented=true})); }
    static int Num(string? s,int min,int max)=>int.TryParse(s,out var v)?Math.Clamp(v,min,max):min;

    void ProfilesList_SelectionChanged(object s, SelectionChangedEventArgs e)
    { current=ProfilesList.SelectedItem as Profile; if(current==null)return; ProfileTitle.Text=current.Name;ProfileNameBox.Text=current.Name;DescriptionBox.Text=current.Description;RowsBox.Text=current.Rows.ToString();ColumnsBox.Text=current.Columns.ToString();PageInfo.Text=$"{current.Rows*current.Columns} ячеек  •  Страница 1 из 1";Rebuild(); }
    void AddProfile_Click(object s,RoutedEventArgs e){var p=Default($"Профиль {profiles.Count+1}","+");profiles.Add(p);ProfilesList.SelectedItem=p;SaveLocal();}
    void DeleteProfile_Click(object s,RoutedEventArgs e){if(current==null||profiles.Count<=1)return;var i=ProfilesList.SelectedIndex;profiles.Remove(current);ProfilesList.SelectedIndex=Math.Max(0,i-1);SaveLocal();}
    void ProfileMenu_Click(object s,RoutedEventArgs e){if(senderProfile(s) is Profile p) ProfilesList.SelectedItem=p;}
    Profile? senderProfile(object s)=>(s as FrameworkElement)?.Tag as Profile;
    async void Save_Click(object s,RoutedEventArgs e){SaveLocal();Rebuild();await Broadcast();}

    void Rebuild()
    {
        if(current==null)return; DeckGrid.Children.Clear();DeckGrid.RowDefinitions.Clear();DeckGrid.ColumnDefinitions.Clear();
        for(int r=0;r<current.Rows;r++)DeckGrid.RowDefinitions.Add(new RowDefinition{Height=new GridLength(116)});
        for(int c=0;c<current.Columns;c++)DeckGrid.ColumnDefinitions.Add(new ColumnDefinition{Width=new GridLength(140)});
        bool[,] used=new bool[current.Rows,current.Columns]; int idx=0;
        foreach(var t in current.Tiles){var pos=FindSpace(used,t,current.Rows,current.Columns);if(pos==null)break;var(r,c)=pos.Value;Mark(used,r,c,t.RowSpan,t.ColumnSpan);var b=new Button{Margin=new Thickness(5),Tag=t,Content=$"{(ShowNumbersBox.IsChecked==true?($"{idx+1}\n"):"")}{t.Title}"};b.Click+=Tile_Click;b.MouseRightButtonUp+=Tile_RightClick;Grid.SetRow(b,r);Grid.SetColumn(b,c);Grid.SetRowSpan(b,Math.Min(t.RowSpan,current.Rows-r));Grid.SetColumnSpan(b,Math.Min(t.ColumnSpan,current.Columns-c));DeckGrid.Children.Add(b);idx++;}
    }
    static (int,int)? FindSpace(bool[,] u,Tile t,int rows,int cols){for(int r=0;r<rows;r++)for(int c=0;c<cols;c++){int rs=Math.Min(t.RowSpan,rows-r),cs=Math.Min(t.ColumnSpan,cols-c);bool ok=true;for(int y=0;y<rs;y++)for(int x=0;x<cs;x++)if(u[r+y,c+x])ok=false;if(ok)return(r,c);}return null;}
    static void Mark(bool[,]u,int r,int c,int rs,int cs){for(int y=0;y<rs&&r+y<u.GetLength(0);y++)for(int x=0;x<cs&&c+x<u.GetLength(1);x++)u[r+y,c+x]=true;}
    void Tile_Click(object s,RoutedEventArgs e){selectedTile=(s as Button)?.Tag as Tile;if(selectedTile!=null&&Keyboard.Modifiers==ModifierKeys.None)Execute(selectedTile.Hotkey);}
    void Tile_RightClick(object s,MouseButtonEventArgs e){selectedTile=(s as Button)?.Tag as Tile;if(selectedTile==null)return;var m=new ContextMenu();foreach(var z in new[]{(1,1),(2,1),(1,2),(2,2),(3,1),(1,3)}){var i=new MenuItem{Header=$"Размер {z.Item1}×{z.Item2}",Tag=z};i.Click+=(_,__)=>{var q=((int,int))i.Tag;selectedTile.ColumnSpan=q.Item1;selectedTile.RowSpan=q.Item2;Rebuild();SaveLocal();};m.Items.Add(i);}m.IsOpen=true;e.Handled=true;}

    IEnumerable<string> KeyActions()=>new[]{"Сохранить — CTRL+S","Скриншот — WIN+SHIFT+S","Переключить окна — ALT+TAB","Рабочий стол — WIN+D","Воспроизведение — MEDIA_PLAY","Выключить звук — VOLUME_MUTE","Копировать — CTRL+C","Вставить — CTRL+V"};
    void ActionsKey_Click(object s,RoutedEventArgs e)=>ActionsList.ItemsSource=KeyActions();
    void ActionsInfo_Click(object s,RoutedEventArgs e)=>ActionsList.ItemsSource=new[]{"Дата и время","Состояние подключения","Название профиля","Страница","Полезные примечания"};
    void ActionsList_DoubleClick(object s,MouseButtonEventArgs e){if(selectedTile==null||ActionsList.SelectedItem is not string a)return;var p=a.Split(" — ");selectedTile.Title=p[0];if(p.Length>1)selectedTile.Hotkey=p[1];Rebuild();SaveLocal();}

    async void ToggleServer_Click(object s,RoutedEventArgs e){if(server==null)await StartServer();else await StopServer();}
    async Task StartServer(){pairCode=Random.Shared.Next(100000,999999).ToString();PairCodeText.Text=$"Код: {pairCode}";var b=WebApplication.CreateBuilder();b.WebHost.UseUrls("http://0.0.0.0:8765");server=b.Build();server.UseWebSockets();server.Map("/ws",async ctx=>{if(ctx.Request.Query["token"]!=pairCode||!ctx.WebSockets.IsWebSocketRequest){ctx.Response.StatusCode=401;return;}var ws=await ctx.WebSockets.AcceptWebSocketAsync();lock(clients)clients.Add(ws);Dispatcher.Invoke(()=>{DeviceText.Text="Телефон подключен";StatusText.Text="● Подключено";});await SendConfig(ws);var buf=new byte[4096];try{while(ws.State==WebSocketState.Open){var r=await ws.ReceiveAsync(buf,CancellationToken.None);if(r.MessageType==WebSocketMessageType.Close)break;var json=Encoding.UTF8.GetString(buf,0,r.Count);using var d=JsonDocument.Parse(json);if(d.RootElement.TryGetProperty("hotkey",out var h))Dispatcher.Invoke(()=>Execute(h.GetString()??""));}}catch{}finally{lock(clients)clients.Remove(ws);Dispatcher.Invoke(()=>{DeviceText.Text=$"{clients.Count} устройств";});}});await server.StartAsync();StatusText.Text="● Сервер запущен";}
    async Task StopServer(){if(server==null)return;await server.StopAsync();await server.DisposeAsync();server=null;lock(clients)clients.Clear();StatusText.Text="● Отключено";DeviceText.Text="Нет подключенных устройств";PairCodeText.Text="";}
    object Snapshot()=>new{type="profile",profile=current};
    async Task SendConfig(WebSocket ws){var data=Encoding.UTF8.GetBytes(JsonSerializer.Serialize(Snapshot()));await ws.SendAsync(data,WebSocketMessageType.Text,true,CancellationToken.None);}
    async Task Broadcast(){List<WebSocket> copy;lock(clients)copy=clients.ToList();foreach(var w in copy.Where(x=>x.State==WebSocketState.Open))try{await SendConfig(w);}catch{}}
    static string LocalIp(){try{return Dns.GetHostEntry(Dns.GetHostName()).AddressList.First(x=>x.AddressFamily==AddressFamily.InterNetwork).ToString();}catch{return "127.0.0.1";}}

    static void Execute(string hotkey){if(string.IsNullOrWhiteSpace(hotkey))return;var keys=hotkey.Split('+',StringSplitOptions.RemoveEmptyEntries|StringSplitOptions.TrimEntries).Select(Vk).Where(x=>x!=0).ToArray();if(keys.Length==0)return;var list=new List<INPUT>();foreach(var k in keys)list.Add(In(k,0));for(int i=keys.Length-1;i>=0;i--)list.Add(In(keys[i],2));SendInput((uint)list.Count,list.ToArray(),Marshal.SizeOf<INPUT>());}
    static ushort Vk(string s){s=s.ToUpperInvariant();if(s.Length==1&&char.IsLetterOrDigit(s[0]))return s[0];if(s.StartsWith("F")&&int.TryParse(s[1..],out var f)&&f>=1&&f<=24)return(ushort)(0x70+f-1);return s switch{"CTRL"=>0x11,"SHIFT"=>0x10,"ALT"=>0x12,"WIN"=>0x5B,"ENTER"=>0x0D,"ESC"=>0x1B,"TAB"=>0x09,"SPACE"=>0x20,"LEFT"=>0x25,"UP"=>0x26,"RIGHT"=>0x27,"DOWN"=>0x28,"MEDIA_PLAY"=>0xB3,"VOLUME_MUTE"=>0xAD,"VOLUME_UP"=>0xAF,"VOLUME_DOWN"=>0xAE,_=>0};}
    static INPUT In(ushort k,uint f)=>new(){type=1,U=new(){ki=new(){wVk=k,dwFlags=f}}};
    [StructLayout(LayoutKind.Sequential)]struct INPUT{public uint type;public UNION U;}[StructLayout(LayoutKind.Explicit)]struct UNION{[FieldOffset(0)]public KEYBDINPUT ki;}[StructLayout(LayoutKind.Sequential)]struct KEYBDINPUT{public ushort wVk,wScan;public uint dwFlags,time;public IntPtr dwExtraInfo;}[DllImport("user32.dll")]static extern uint SendInput(uint n,INPUT[] p,int cb);
    protected override async void OnClosed(EventArgs e){SaveLocal();if(server!=null)await StopServer();base.OnClosed(e);}
}
public class Profile{public string Name{get;set;}="Profile";public string Icon{get;set;}="■";public string Description{get;set;}="";public int Rows{get;set;}=3;public int Columns{get;set;}=4;public List<Tile> Tiles{get;set;}=new();}
public class Tile{public string Title{get;set;}="Добавить";public string Hotkey{get;set;}="";public int RowSpan{get;set;}=1;public int ColumnSpan{get;set;}=1;}
