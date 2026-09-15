using System.Collections.ObjectModel;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Net.WebSockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using QRCoder;

namespace MacroPadRemote;

public partial class MainWindow : Window
{
    readonly string statePath;
    readonly ObservableCollection<Profile> profiles = new();
    readonly List<WebSocket> clients = new();
    readonly JsonSerializerOptions json = new() { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    AppState state = new(); Profile? profile; DeckPage? page; Tile? selected; Button? selectedButton;
    WebApplication? server; string pairCode = ""; bool updating; double fitScale = 1, userZoom = 1;

    public MainWindow()
    {
        InitializeComponent();
        var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "MacroPadRemote");
        Directory.CreateDirectory(dir); statePath = Path.Combine(dir, "presets.json");
        LoadState(); ProfileBox.ItemsSource = profiles; ActionsList.ItemsSource = Actions();
        ApplyTransport(); RefreshProfiles();
        Loaded += (_, _) => Dispatcher.BeginInvoke(UpdateZoom, DispatcherPriority.Loaded);
    }

    void LoadState()
    {
        try { if (File.Exists(statePath)) state = JsonSerializer.Deserialize<AppState>(File.ReadAllText(statePath), json) ?? new(); } catch { state = new(); }
        if (state.Profiles.Count == 0)
        {
            state.Profiles.Add(DefaultProfile("Revit", "R"));
            state.Profiles.Add(DefaultProfile("NanoCAD", "N"));
            state.Profiles.Add(DefaultProfile("Рабочий стол", "▣"));
            state.ActiveProfileId = state.Profiles[0].Id;
        }
        foreach (var p in state.Profiles) { if (p.Pages.Count == 0) p.Pages.Add(DefaultPage("Страница 1")); if (string.IsNullOrWhiteSpace(p.ActivePageId)) p.ActivePageId = p.Pages[0].Id; foreach (var pg in p.Pages) EnsureCapacity(pg); profiles.Add(p); }
    }
    void SaveState() { state.Profiles = profiles.ToList(); if (profile != null) state.ActiveProfileId = profile.Id; try { File.WriteAllText(statePath, JsonSerializer.Serialize(state, json)); } catch { } }
    static Profile DefaultProfile(string name, string icon) { var p = new Profile { Name = name, Icon = icon }; var pg = DefaultPage("Страница 1"); p.Pages.Add(pg); p.ActivePageId = pg.Id; return p; }
    static DeckPage DefaultPage(string name)
    {
        var pg = new DeckPage { Name = name, Rows = 3, Columns = 4 };
        string[] n = ["Сохранить","Скриншот","Переключить окна","Браузер","Назад","Воспроизведение","Выключить звук","Рабочий стол","Почта","Калькулятор","Открыть папку","Добавить"];
        string[] h = ["CTRL+S","WIN+SHIFT+S","ALT+TAB","CTRL+L","ESC","MEDIA_PLAY","VOLUME_MUTE","WIN+D","","","",""];
        for (int i=0;i<n.Length;i++) pg.Tiles.Add(new Tile { Title=n[i], Hotkey=h[i] }); return pg;
    }

    void RefreshProfiles()
    {
        updating=true; ProfileBox.ItemsSource=null; ProfileBox.ItemsSource=profiles;
        profile = profiles.FirstOrDefault(x=>x.Id==state.ActiveProfileId) ?? profiles.First(); ProfileBox.SelectedItem=profile; updating=false; LoadProfile();
    }
    void LoadProfile()
    {
        if (profile==null) return; if (profile.Pages.Count==0) profile.Pages.Add(DefaultPage("Страница 1"));
        page=profile.Pages.FirstOrDefault(x=>x.Id==profile.ActivePageId) ?? profile.Pages[0]; profile.ActivePageId=page.Id;
        updating=true; ProfileTitle.Text=profile.Name; ProfileName.Text=profile.Name; ProfileDescription.Text=profile.Description; ColumnsBox.Text=page.Columns.ToString(); RowsBox.Text=page.Rows.ToString(); userZoom=Math.Clamp(page.Zoom,ZoomSlider.Minimum,ZoomSlider.Maximum); ZoomSlider.Value=userZoom;
        PageBox.ItemsSource=null; PageBox.ItemsSource=profile.Pages; PageBox.SelectedItem=page; updating=false; RebuildPages(); RebuildGrid();
    }
    void RebuildPages()
    {
        if (profile==null||page==null) return; PageButtons.Children.Clear(); int idx=profile.Pages.IndexOf(page)+1; PageInfo.Text=$"Страница {idx} из {profile.Pages.Count}";
        for(int i=0;i<profile.Pages.Count;i++){var pg=profile.Pages[i]; var b=new Button{Content=(i+1).ToString(),Width=34,Height=32,Margin=new Thickness(3,0,3,0),Tag=pg,Background=pg.Id==page.Id?Brushes.White:(Brush)FindResource("Panel2"),Foreground=pg.Id==page.Id?Brushes.Black:Brushes.White}; b.Click+=(_,_)=>{profile.ActivePageId=pg.Id;SaveState();LoadProfile();_=Broadcast();};PageButtons.Children.Add(b);}
    }
    void RebuildGrid()
    {
        if(page==null)return; EnsureCapacity(page); DeckGrid.Children.Clear();DeckGrid.RowDefinitions.Clear();DeckGrid.ColumnDefinitions.Clear();
        for(int r=0;r<page.Rows;r++)DeckGrid.RowDefinitions.Add(new RowDefinition{Height=new GridLength(116)}); for(int c=0;c<page.Columns;c++)DeckGrid.ColumnDefinitions.Add(new ColumnDefinition{Width=new GridLength(142)});
        GridInfo.Text=$"{page.Columns} × {page.Rows}  •  {page.Columns*page.Rows} ячеек"; bool[,] used=new bool[page.Rows,page.Columns]; int no=1;
        foreach(var t in page.Tiles){var pos=FindSpace(used,t,page.Rows,page.Columns);if(pos==null)continue;var(r,c)=pos.Value;int rs=Math.Min(Math.Max(1,t.RowSpan),page.Rows-r),cs=Math.Min(Math.Max(1,t.ColumnSpan),page.Columns-c);Mark(used,r,c,rs,cs);var b=TileButton(t,no++);Grid.SetRow(b,r);Grid.SetColumn(b,c);Grid.SetRowSpan(b,rs);Grid.SetColumnSpan(b,cs);DeckGrid.Children.Add(b);} Dispatcher.BeginInvoke(UpdateZoom,DispatcherPriority.Background);
    }
    Button TileButton(Tile t,int no)
    {
        bool blank=IsBlank(t); var b=new Button{Tag=t,Margin=new Thickness(5),Padding=new Thickness(10),MinWidth=125,MinHeight=100,Background=new SolidColorBrush(blank?Color.FromRgb(32,35,38):Color.FromRgb(39,43,46)),BorderBrush=new SolidColorBrush(Color.FromRgb(20,22,24)),BorderThickness=new Thickness(2)};
        var root=new Grid();var sp=new StackPanel{HorizontalAlignment=HorizontalAlignment.Center,VerticalAlignment=VerticalAlignment.Center};sp.Children.Add(new TextBlock{Text=Glyph(t),FontSize=26,HorizontalAlignment=HorizontalAlignment.Center,Margin=new Thickness(0,0,0,7),Foreground=blank?Brushes.Gray:Brushes.White});sp.Children.Add(new TextBlock{Text=t.Title,TextAlignment=TextAlignment.Center,TextWrapping=TextWrapping.Wrap,FontWeight=FontWeights.SemiBold,Foreground=blank?Brushes.Gray:Brushes.White,MaxWidth=180});if(!string.IsNullOrWhiteSpace(t.Hotkey))sp.Children.Add(new TextBlock{Text=t.Hotkey,FontSize=9,Foreground=(Brush)FindResource("Muted"),HorizontalAlignment=HorizontalAlignment.Center,Margin=new Thickness(0,4,0,0)});root.Children.Add(sp);if(ShowNumbers.IsChecked==true)root.Children.Add(new TextBlock{Text=no.ToString(),FontSize=10,Foreground=Brushes.Gray,HorizontalAlignment=HorizontalAlignment.Left,VerticalAlignment=VerticalAlignment.Top});b.Content=root;
        b.Click+=(_,_)=>SelectTile(b,t); b.MouseDoubleClick+=(_,_)=>FocusTile(b); b.ContextMenu=TileMenu(t); return b;
    }
    void SelectTile(Button b,Tile t){if(selectedButton!=null)selectedButton.BorderBrush=new SolidColorBrush(Color.FromRgb(20,22,24));selectedButton=b;selected=t;b.BorderBrush=(Brush)FindResource("Blue");}
    ContextMenu TileMenu(Tile t)
    {
        var m=new ContextMenu();var edit=new MenuItem{Header="Редактировать макрос…"};edit.Click+=(_,_)=>EditTile(t);m.Items.Add(edit);m.Items.Add(new Separator());var size=new MenuItem{Header="Размер ячейки"};foreach(var o in new[]{("1 × 1",1,1),("2 × 1",2,1),("1 × 2",1,2),("2 × 2",2,2),("3 × 1",3,1),("1 × 3",1,3)}){int c=o.Item2,r=o.Item3;var i=new MenuItem{Header=o.Item1,IsCheckable=true,IsChecked=t.ColumnSpan==c&&t.RowSpan==r};i.Click+=(_,_)=>ResizeTile(t,c,r);size.Items.Add(i);}m.Items.Add(size);var clear=new MenuItem{Header="Очистить ячейку"};clear.Click+=(_,_)=>{t.Title="Добавить";t.Hotkey="";t.ColumnSpan=t.RowSpan=1;EnsureCapacity(page!);SaveAndBroadcast();};m.Items.Add(clear);return m;
    }
    void EditTile(Tile t)
    {
        var w=new Window{Owner=this,Title="Макрос",Width=430,Height=260,ResizeMode=ResizeMode.NoResize,WindowStartupLocation=WindowStartupLocation.CenterOwner,Background=(Brush)FindResource("Bg")};var g=new Grid{Margin=new Thickness(18)};for(int i=0;i<5;i++)g.RowDefinitions.Add(new RowDefinition{Height=i is 1 or 3?new GridLength(38):GridLength.Auto});var title=new TextBox{Text=t.Title};var key=new TextBox{Text=t.Hotkey};g.Children.Add(new TextBlock{Text="Название"});Grid.SetRow(title,1);g.Children.Add(title);var l=new TextBlock{Text="Команда / горячая клавиша",Margin=new Thickness(0,8,0,3)};Grid.SetRow(l,2);g.Children.Add(l);Grid.SetRow(key,3);g.Children.Add(key);var buttons=new StackPanel{Orientation=Orientation.Horizontal,HorizontalAlignment=HorizontalAlignment.Right,Margin=new Thickness(0,12,0,0)};var cancel=new Button{Content="Отмена",Width=90,Margin=new Thickness(0,0,8,0)};cancel.Click+=(_,_)=>w.Close();var ok=new Button{Content="Сохранить",Width=100};ok.Click+=(_,_)=>{t.Title=string.IsNullOrWhiteSpace(title.Text)?"Кнопка":title.Text.Trim();t.Hotkey=key.Text.Trim().ToUpperInvariant();w.DialogResult=true;};buttons.Children.Add(cancel);buttons.Children.Add(ok);Grid.SetRow(buttons,4);g.Children.Add(buttons);w.Content=g;if(w.ShowDialog()==true)SaveAndBroadcast();
    }
    void ResizeTile(Tile t,int cols,int rows)
    {
        if(page==null)return;cols=Math.Clamp(cols,1,page.Columns);rows=Math.Clamp(rows,1,page.Rows);int extra=cols*rows-Math.Max(1,t.ColumnSpan)*Math.Max(1,t.RowSpan);if(extra>0){var blanks=page.Tiles.Where(x=>!ReferenceEquals(x,t)&&IsBlank(x)).Take(extra).ToList();if(blanks.Count<extra){MessageBox.Show(this,"Недостаточно свободных пустых ячеек.","MacroPad Remote");return;}foreach(var x in blanks)page.Tiles.Remove(x);}t.ColumnSpan=cols;t.RowSpan=rows;EnsureCapacity(page);SaveAndBroadcast();
    }
    static (int,int)? FindSpace(bool[,] u,Tile t,int rows,int cols){int rs=Math.Max(1,t.RowSpan),cs=Math.Max(1,t.ColumnSpan);for(int r=0;r<rows;r++)for(int c=0;c<cols;c++){if(r+rs>rows||c+cs>cols)continue;bool ok=true;for(int y=0;y<rs&&ok;y++)for(int x=0;x<cs;x++)if(u[r+y,c+x]){ok=false;break;}if(ok)return(r,c);}return null;}
    static void Mark(bool[,]u,int r,int c,int rs,int cs){for(int y=0;y<rs;y++)for(int x=0;x<cs;x++)u[r+y,c+x]=true;}
    static bool IsBlank(Tile t)=>string.IsNullOrWhiteSpace(t.Hotkey)&&t.Title.Equals("Добавить",StringComparison.OrdinalIgnoreCase);
    static int UsedArea(DeckPage p)=>p.Tiles.Sum(t=>Math.Max(1,t.RowSpan)*Math.Max(1,t.ColumnSpan));
    static int ConfiguredArea(DeckPage p)=>p.Tiles.Where(t=>!IsBlank(t)).Sum(t=>Math.Max(1,t.RowSpan)*Math.Max(1,t.ColumnSpan));
    static void EnsureCapacity(DeckPage p){p.Rows=Math.Clamp(p.Rows,1,12);p.Columns=Math.Clamp(p.Columns,1,12);int target=p.Rows*p.Columns;while(UsedArea(p)<target)p.Tiles.Add(new Tile());while(UsedArea(p)>target){var b=p.Tiles.LastOrDefault(IsBlank);if(b==null)break;p.Tiles.Remove(b);}}
    static string Glyph(Tile t){var s=t.Title.ToLowerInvariant();if(s.Contains("сохран"))return"▣";if(s.Contains("скрин"))return"⌗";if(s.Contains("брауз"))return"◎";if(s.Contains("пап"))return"□";if(s.Contains("звук"))return"◖";if(s.Contains("восп"))return"▶";if(s.Contains("назад"))return"←";return IsBlank(t)?"+":"⌨";}

    void UpdateZoom(){if(page==null||!IsLoaded)return;DeckGrid.Measure(new Size(double.PositiveInfinity,double.PositiveInfinity));var d=DeckGrid.DesiredSize;if(d.Width<=0||d.Height<=0)return;double w=Math.Max(1,DeckViewport.ViewportWidth-48),h=Math.Max(1,DeckViewport.ViewportHeight-48);fitScale=Math.Clamp(Math.Min(w/d.Width,h/d.Height),.28,1);DeckScaleHost.LayoutTransform=new ScaleTransform(fitScale*userZoom,fitScale*userZoom);}
    void DeckViewport_SizeChanged(object s,SizeChangedEventArgs e)=>UpdateZoom();
    void ZoomSlider_ValueChanged(object s,RoutedPropertyChangedEventArgs<double> e){if(updating||page==null||!IsLoaded)return;userZoom=ZoomSlider.Value;page.Zoom=userZoom;SaveState();UpdateZoom();}
    void DeckViewport_PreviewMouseWheel(object s,MouseWheelEventArgs e){if((Keyboard.Modifiers&ModifierKeys.Control)==0)return;e.Handled=true;var p=e.GetPosition(DeckViewport);double old=Math.Max(.01,fitScale*userZoom),lx=(DeckViewport.HorizontalOffset+p.X)/old,ly=(DeckViewport.VerticalOffset+p.Y)/old;userZoom=Math.Clamp(userZoom+(e.Delta>0?.12:-.12),ZoomSlider.Minimum,ZoomSlider.Maximum);updating=true;ZoomSlider.Value=userZoom;updating=false;if(page!=null)page.Zoom=userZoom;SaveState();UpdateZoom();Dispatcher.BeginInvoke(()=>{double n=fitScale*userZoom;DeckViewport.ScrollToHorizontalOffset(Math.Max(0,lx*n-p.X));DeckViewport.ScrollToVerticalOffset(Math.Max(0,ly*n-p.Y));},DispatcherPriority.Background);}
    void FocusTile(FrameworkElement el){userZoom=Math.Max(userZoom,1.5);updating=true;ZoomSlider.Value=userZoom;updating=false;if(page!=null)page.Zoom=userZoom;UpdateZoom();Dispatcher.BeginInvoke(()=>{try{var b=el.TransformToAncestor(DeckGrid).TransformBounds(new Rect(new Point(),el.RenderSize));double s=fitScale*userZoom;DeckViewport.ScrollToHorizontalOffset(Math.Max(0,(b.Left+b.Width/2)*s-DeckViewport.ViewportWidth/2));DeckViewport.ScrollToVerticalOffset(Math.Max(0,(b.Top+b.Height/2)*s-DeckViewport.ViewportHeight/2));}catch{}},DispatcherPriority.Background);}

    void ProfileBox_SelectionChanged(object s,SelectionChangedEventArgs e){if(updating||ProfileBox.SelectedItem is not Profile p)return;profile=p;state.ActiveProfileId=p.Id;SaveState();LoadProfile();_=Broadcast();}
    void PageBox_SelectionChanged(object s,SelectionChangedEventArgs e){if(updating||profile==null||PageBox.SelectedItem is not DeckPage p)return;profile.ActivePageId=p.Id;SaveState();LoadProfile();_=Broadcast();}
    void AddProfile_Click(object s,RoutedEventArgs e){var n=Prompt("Новый профиль",$"Профиль {profiles.Count+1}");if(n==null)return;var p=DefaultProfile(n,n[..1].ToUpperInvariant());profiles.Add(p);state.ActiveProfileId=p.Id;SaveState();RefreshProfiles();}
    void DeleteProfile_Click(object s,RoutedEventArgs e){if(profile==null||profiles.Count<=1)return;if(MessageBox.Show(this,$"Удалить профиль «{profile.Name}»?","MacroPad Remote",MessageBoxButton.YesNo)!=MessageBoxResult.Yes)return;profiles.Remove(profile);state.ActiveProfileId=profiles[0].Id;SaveState();RefreshProfiles();_=Broadcast();}
    void ProfileMenu_Click(object s,RoutedEventArgs e){if(s is not Button{Tag:Profile p} b)return;ProfileBox.SelectedItem=p;var m=new ContextMenu();var ren=new MenuItem{Header="Переименовать"};ren.Click+=(_,_)=>{var n=Prompt("Переименовать профиль",p.Name);if(n==null)return;p.Name=n;SaveState();RefreshProfiles();};var copy=new MenuItem{Header="Создать копию"};copy.Click+=(_,_)=>{var x=JsonSerializer.Deserialize<Profile>(JsonSerializer.Serialize(p,json),json)!;x.Id=Guid.NewGuid().ToString("N");x.Name+=" copy";foreach(var pg in x.Pages){pg.Id=Guid.NewGuid().ToString("N");foreach(var t in pg.Tiles)t.Id=Guid.NewGuid().ToString("N");}x.ActivePageId=x.Pages[0].Id;profiles.Add(x);state.ActiveProfileId=x.Id;SaveState();RefreshProfiles();};var del=new MenuItem{Header="Удалить"};del.Click+=DeleteProfile_Click;m.Items.Add(ren);m.Items.Add(copy);m.Items.Add(new Separator());m.Items.Add(del);b.ContextMenu=m;m.PlacementTarget=b;m.IsOpen=true;e.Handled=true;}
    void AddPage_Click(object s,RoutedEventArgs e){if(profile==null)return;var n=Prompt("Новая страница",$"Страница {profile.Pages.Count+1}");if(n==null)return;var pg=DefaultPage(n);profile.Pages.Add(pg);profile.ActivePageId=pg.Id;SaveState();LoadProfile();_=Broadcast();}
    void SaveProfile_Click(object s,RoutedEventArgs e){if(profile==null||page==null)return;if(!string.IsNullOrWhiteSpace(ProfileName.Text))profile.Name=ProfileName.Text.Trim();profile.Description=ProfileDescription.Text.Trim();int cols=int.TryParse(ColumnsBox.Text,out var c)?Math.Clamp(c,1,12):page.Columns,rows=int.TryParse(RowsBox.Text,out var r)?Math.Clamp(r,1,12):page.Rows;if(ConfiguredArea(page)>cols*rows){MessageBox.Show(this,"Новая сетка слишком мала для уже настроенных плиток.","MacroPad Remote");return;}page.Columns=cols;page.Rows=rows;EnsureCapacity(page);SaveState();RefreshProfiles();_=Broadcast();}
    void ActionsList_DoubleClick(object s,MouseButtonEventArgs e){if(selected==null||ActionsList.SelectedItem is not ActionItem a)return;selected.Title=a.Title;selected.Hotkey=a.Hotkey;SaveAndBroadcast();}
    static List<ActionItem> Actions()=>[new("Сохранить","CTRL+S"),new("Скриншот","WIN+SHIFT+S"),new("Переключить окна","ALT+TAB"),new("Рабочий стол","WIN+D"),new("Копировать","CTRL+C"),new("Вставить","CTRL+V"),new("Отменить","CTRL+Z"),new("Воспроизведение","MEDIA_PLAY"),new("Выключить звук","VOLUME_MUTE")];

    string SelectedTransport()=>TransportBox.SelectedItem is ComboBoxItem i&&Equals(i.Tag?.ToString(),"Bluetooth")?"Bluetooth":"Wifi";
    void ApplyTransport(){updating=true;string wanted=state.Transport=="Bluetooth"?"Bluetooth":"Wifi";foreach(var i in TransportBox.Items.OfType<ComboBoxItem>())if(i.Tag?.ToString()==wanted){TransportBox.SelectedItem=i;break;}updating=false;SyncConnectionUi();}
    async void TransportBox_SelectionChanged(object s,SelectionChangedEventArgs e){if(updating)return;if(server!=null)await StopServer();state.Transport=SelectedTransport();SaveState();SyncConnectionUi();}
    void SyncConnectionUi(){bool wifi=SelectedTransport()=="Wifi";DeviceQrButton.IsEnabled=HeaderQrButton.IsEnabled=wifi;string text=server!=null?"Остановить связь":wifi?"Запустить связь":"Bluetooth — скоро";DeviceServerButton.Content=HeaderServerButton.Content=text;if(server==null){DeviceStatus.Text=wifi?"Связь не запущена":"Bluetooth выбран";ConnectionDetails.Text=wifi?"Wi‑Fi: запуск сервера + QR-код":"BLE-транспорт будет следующим этапом";}}
    async void ServerButton_Click(object s,RoutedEventArgs e){if(SelectedTransport()=="Bluetooth"){MessageBox.Show(this,"Bluetooth уже добавлен как режим подключения. В этой preview-сборке реальный BLE-транспорт ещё не активирован; используйте Wi‑Fi + QR-код.","MacroPad Remote");return;}try{if(server==null)await StartServer();else await StopServer();}catch(Exception ex){MessageBox.Show(this,$"Не удалось изменить состояние связи.\n\n{ex.Message}","MacroPad Remote");}}
    async Task StartServer()
    {
        pairCode=Random.Shared.Next(100000,999999).ToString();var b=WebApplication.CreateBuilder();b.WebHost.UseUrls("http://0.0.0.0:8765");var app=b.Build();app.UseWebSockets();app.Map("/ws",async ctx=>{if(!ctx.WebSockets.IsWebSocketRequest||ctx.Request.Query["token"]!=pairCode){ctx.Response.StatusCode=401;return;}var ws=await ctx.WebSockets.AcceptWebSocketAsync();lock(clients)clients.Add(ws);Dispatcher.Invoke(UpdateConnectionStatus);await SendConfig(ws);var buf=new byte[8192];try{while(ws.State==WebSocketState.Open){var r=await ws.ReceiveAsync(buf,CancellationToken.None);if(r.MessageType==WebSocketMessageType.Close)break;using var doc=JsonDocument.Parse(Encoding.UTF8.GetString(buf,0,r.Count));if(doc.RootElement.TryGetProperty("hotkey",out var h))Dispatcher.Invoke(()=>ExecuteHotkey(h.GetString()??""));}}catch{}finally{lock(clients)clients.Remove(ws);Dispatcher.Invoke(UpdateConnectionStatus);}});await app.StartAsync();server=app;DeviceStatus.Text="Wi‑Fi активен";ConnectionDetails.Text=$"{LocalIp()}:8765  •  код {pairCode}";SyncConnectionUi();UpdateConnectionStatus();
    }
    async Task StopServer(){if(server==null)return;await server.StopAsync();await server.DisposeAsync();server=null;lock(clients)clients.Clear();SyncConnectionUi();UpdateConnectionStatus();}
    void UpdateConnectionStatus(){int count;lock(clients)count=clients.Count;HeaderStatus.Text=count==0?(server==null?"Нет подключенных телефонов":"Сервер запущен"):count==1?"Подключен 1 телефон":$"Подключено: {count}";HeaderDot.Foreground=count>0?(Brush)FindResource("Green"):server!=null?Brushes.Gold:(Brush)FindResource("Muted");}
    void ShowQr_Click(object s,RoutedEventArgs e){if(SelectedTransport()!="Wifi"){MessageBox.Show(this,"QR-код используется для Wi‑Fi подключения.","MacroPad Remote");return;}if(server==null){MessageBox.Show(this,"Сначала запустите связь по Wi‑Fi.","MacroPad Remote");return;}ShowQr(LocalIp(),8765,pairCode);}
    void ShowQr(string host,int port,string token)
    {
        string payload=$"macropad://connect?host={Uri.EscapeDataString(host)}&port={port}&token={Uri.EscapeDataString(token)}";using var gen=new QRCodeGenerator();using var data=gen.CreateQrCode(payload,QRCodeGenerator.ECCLevel.Q);byte[] png=new PngByteQRCode(data).GetGraphic(12);var bmp=new BitmapImage();using(var ms=new MemoryStream(png)){bmp.BeginInit();bmp.CacheOption=BitmapCacheOption.OnLoad;bmp.StreamSource=ms;bmp.EndInit();bmp.Freeze();}var w=new Window{Owner=this,Title="Быстрое подключение",Width=430,Height=515,ResizeMode=ResizeMode.NoResize,WindowStartupLocation=WindowStartupLocation.CenterOwner,Background=(Brush)FindResource("Bg")};var sp=new StackPanel{Margin=new Thickness(22)};sp.Children.Add(new TextBlock{Text="Подключить телефон",FontSize=22,FontWeight=FontWeights.SemiBold,HorizontalAlignment=HorizontalAlignment.Center});sp.Children.Add(new TextBlock{Text="В мобильном приложении нажмите «Сканировать QR». IP и код заполнятся автоматически.",Foreground=(Brush)FindResource("Muted"),TextAlignment=TextAlignment.Center,TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,8,0,14)});sp.Children.Add(new Border{Background=Brushes.White,Padding=new Thickness(12),HorizontalAlignment=HorizontalAlignment.Center,Child=new Image{Width=290,Height=290,Source=bmp}});sp.Children.Add(new TextBlock{Text=$"{host}:{port}    Код: {token}",FontWeight=FontWeights.SemiBold,TextAlignment=TextAlignment.Center,Margin=new Thickness(0,14,0,0)});w.Content=sp;w.ShowDialog();
    }

    object Snapshot()=>new{type="profile",profile=profile==null||page==null?null:new{name=profile.Name,rows=page.Rows,columns=page.Columns,tiles=page.Tiles.Select(t=>new{title=t.Title,hotkey=t.Hotkey,rowSpan=t.RowSpan,columnSpan=t.ColumnSpan}).ToList()}};
    async Task SendConfig(WebSocket ws){byte[] bytes=Encoding.UTF8.GetBytes(JsonSerializer.Serialize(Snapshot(),json));await ws.SendAsync(bytes,WebSocketMessageType.Text,true,CancellationToken.None);}
    async Task Broadcast(){List<WebSocket> copy;lock(clients)copy=clients.Where(x=>x.State==WebSocketState.Open).ToList();foreach(var ws in copy)try{await SendConfig(ws);}catch{}}
    void SaveAndBroadcast(){if(page!=null)EnsureCapacity(page);SaveState();RebuildGrid();_=Broadcast();}
    static string LocalIp(){try{return Dns.GetHostEntry(Dns.GetHostName()).AddressList.First(x=>x.AddressFamily==AddressFamily.InterNetwork&&!IPAddress.IsLoopback(x)).ToString();}catch{return"127.0.0.1";}}
    string? Prompt(string title,string initial){var w=new Window{Owner=this,Title=title,Width=390,Height=165,ResizeMode=ResizeMode.NoResize,WindowStartupLocation=WindowStartupLocation.CenterOwner,Background=(Brush)FindResource("Bg")};var g=new Grid{Margin=new Thickness(16)};g.RowDefinitions.Add(new RowDefinition{Height=new GridLength(38)});g.RowDefinitions.Add(new RowDefinition());var box=new TextBox{Text=initial,Height=34};g.Children.Add(box);var sp=new StackPanel{Orientation=Orientation.Horizontal,HorizontalAlignment=HorizontalAlignment.Right,VerticalAlignment=VerticalAlignment.Bottom};var cancel=new Button{Content="Отмена",Width=85,Margin=new Thickness(0,0,7,0)};cancel.Click+=(_,_)=>w.Close();var ok=new Button{Content="OK",Width=85};ok.Click+=(_,_)=>w.DialogResult=true;sp.Children.Add(cancel);sp.Children.Add(ok);Grid.SetRow(sp,1);g.Children.Add(sp);w.Content=g;box.SelectAll();box.Focus();return w.ShowDialog()==true&&!string.IsNullOrWhiteSpace(box.Text)?box.Text.Trim():null;}

    static void ExecuteHotkey(string hotkey){if(string.IsNullOrWhiteSpace(hotkey))return;var keys=hotkey.Split('+',StringSplitOptions.RemoveEmptyEntries|StringSplitOptions.TrimEntries).Select(Vk).Where(x=>x!=0).ToArray();if(keys.Length==0)return;var input=new List<INPUT>();foreach(var k in keys)input.Add(Key(k,0));for(int i=keys.Length-1;i>=0;i--)input.Add(Key(keys[i],2));SendInput((uint)input.Count,input.ToArray(),Marshal.SizeOf<INPUT>());}
    static ushort Vk(string s){s=s.ToUpperInvariant();if(s.Length==1&&char.IsLetterOrDigit(s[0]))return s[0];if(s.StartsWith('F')&&int.TryParse(s[1..],out int f)&&f>=1&&f<=24)return(ushort)(0x70+f-1);return s switch{"CTRL"=>0x11,"SHIFT"=>0x10,"ALT"=>0x12,"WIN"=>0x5B,"ENTER"=>0x0D,"ESC"=>0x1B,"TAB"=>0x09,"SPACE"=>0x20,"LEFT"=>0x25,"UP"=>0x26,"RIGHT"=>0x27,"DOWN"=>0x28,"MEDIA_PLAY"=>0xB3,"VOLUME_MUTE"=>0xAD,"VOLUME_UP"=>0xAF,"VOLUME_DOWN"=>0xAE,_=>0};}
    static INPUT Key(ushort k,uint f)=>new(){type=1,U=new(){ki=new(){wVk=k,dwFlags=f}}};
    [StructLayout(LayoutKind.Sequential)]struct INPUT{public uint type;public INPUTUNION U;}[StructLayout(LayoutKind.Explicit)]struct INPUTUNION{[FieldOffset(0)]public KEYBDINPUT ki;}[StructLayout(LayoutKind.Sequential)]struct KEYBDINPUT{public ushort wVk,wScan;public uint dwFlags,time;public IntPtr dwExtraInfo;}[DllImport("user32.dll")]static extern uint SendInput(uint n,INPUT[] p,int cb);
    protected override async void OnClosed(EventArgs e){SaveState();if(server!=null)await StopServer();base.OnClosed(e);}
}

public sealed class AppState{public string ActiveProfileId{get;set;}="";public string Transport{get;set;}="Wifi";public List<Profile> Profiles{get;set;}=new();}
public sealed class Profile{public string Id{get;set;}=Guid.NewGuid().ToString("N");public string Name{get;set;}="Profile";public string Icon{get;set;}="■";public string Description{get;set;}="";public string ActivePageId{get;set;}="";public List<DeckPage> Pages{get;set;}=new();}
public sealed class DeckPage{public string Id{get;set;}=Guid.NewGuid().ToString("N");public string Name{get;set;}="Страница";public int Rows{get;set;}=3;public int Columns{get;set;}=4;public double Zoom{get;set;}=1;public List<Tile> Tiles{get;set;}=new();}
public sealed class Tile{public string Id{get;set;}=Guid.NewGuid().ToString("N");public string Title{get;set;}="Добавить";public string Hotkey{get;set;}="";public int RowSpan{get;set;}=1;public int ColumnSpan{get;set;}=1;}
public sealed record ActionItem(string Title,string Hotkey){public override string ToString()=>string.IsNullOrWhiteSpace(Hotkey)?Title:$"{Title} — {Hotkey}";}
