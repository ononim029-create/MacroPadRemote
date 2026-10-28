package com.domokrat.nodera.mobile;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Callable;
import java.util.function.Consumer;

/** Native NODERA management client. File contents are never requested or opened. */
public final class MainActivity extends Activity {
    private static final int BG = Color.rgb(8, 22, 37);
    private static final int PANEL = Color.rgb(19, 40, 59);
    private static final int BLUE = Color.rgb(34, 137, 244);
    private static final int TEXT = Color.rgb(240, 247, 255);
    private static final int MUTED = Color.rgb(169, 195, 213);
    private static final int BORDER = Color.rgb(54, 85, 110);
    private static final int RED = Color.rgb(241, 111, 126);
    private static final String PREF = "nodera_native_app_v1";
    private static final long POLL_MS = 10_000;

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());
    private LinearLayout root, body, header, tabs;
    private ProgressBar progress;
    private TextView serverLabel, headerTitle;
    private NoderaApi api;
    private SecureIdentity identity;
    private String origin = "";
    private String folder = "/";
    private String tab = "files";
    private JSONObject me = new JSONObject();
    private JSONArray profiles = new JSONArray();
    private boolean busy = false, active = false, pending = false;
    private int unread = 0;
    private String generatedInvite = "";
    private String generatedInviteNote = "";
    private final Runnable poll = new Runnable() {
        @Override public void run() {
            if (!active) return;
            if (!busy && api != null) {
                if (pending) checkPending(true);
                else if (tab.equals("notifications") || tab.equals("requests") || tab.equals("devices")) loadCurrent(true);
                else worker.execute(() -> {
                    try {
                        JSONObject feed = api.get("/v1/notifications");
                        ui.post(() -> { unread = feed.optInt("unread"); nav(); });
                    } catch (Exception ignored) { /* Connectivity errors appear on explicit refresh. */ }
                });
            }
            ui.postDelayed(this, POLL_MS);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);
        root.setFitsSystemWindows(true);
        setContentView(root);
        buildChrome();
        String inbound = inviteFromIntent(getIntent());
        String saved = getPreferences(MODE_PRIVATE).getString("server", "");
        if (!inbound.isEmpty()) showSetup(inbound, "Ссылка NODERA получена. Укажите ваше имя и отправьте запрос на сервер.");
        else if (!saved.isEmpty()) connect(saved, getPreferences(MODE_PRIVATE).getString("user", ""), "");
        else showSetup("", "");
    }

    private int dp(int value) { return Math.round(getResources().getDisplayMetrics().density * value); }
    private GradientDrawable background(int color, int stroke, int radius) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(radius));
        if (stroke != 0) shape.setStroke(dp(1), stroke);
        return shape;
    }
    private TextView text(String value, int sp, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextColor(color);
        view.setTextSize(sp);
        view.setLineSpacing(dp(3), 1f);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }
    private void pad(View view, int h, int v) { view.setPadding(dp(h), dp(v), dp(h), dp(v)); }
    private LinearLayout column() {
        LinearLayout view = new LinearLayout(this);
        view.setOrientation(LinearLayout.VERTICAL);
        return view;
    }
    private LinearLayout row() {
        LinearLayout view = new LinearLayout(this);
        view.setOrientation(LinearLayout.HORIZONTAL);
        view.setGravity(Gravity.CENTER_VERTICAL);
        return view;
    }
    private void gap(LinearLayout view, int px) {
        View spacer = new View(this);
        view.addView(spacer, new LinearLayout.LayoutParams(1, dp(px)));
    }
    private LinearLayout card() {
        LinearLayout c = column();
        c.setBackground(background(PANEL, BORDER, 18));
        pad(c, 16, 16);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.setMargins(dp(14), dp(7), dp(14), dp(7));
        body.addView(c, lp);
        return c;
    }
    private void line(LinearLayout into, String value, int sp, int color, boolean bold) {
        TextView t = text(value, sp, color, bold);
        into.addView(t, new LinearLayout.LayoutParams(-1, -2));
    }
    private Button button(String title, boolean primary, Runnable action) {
        Button b = new Button(this);
        b.setText(title);
        b.setAllCaps(false);
        b.setTextSize(14);
        b.setTextColor(TEXT);
        b.setBackground(background(primary ? BLUE : PANEL, primary ? 0 : BORDER, 13));
        b.setElevation(0f);
        b.setMinHeight(dp(46));
        pad(b, 12, 8);
        b.setOnClickListener(v -> { if (!busy) action.run(); });
        return b;
    }
    private void addButton(LinearLayout target, String title, boolean primary, Runnable action) {
        Button b = button(title, primary, action);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, dp(46));
        lp.topMargin = dp(10);
        target.addView(b, lp);
    }
    private EditText edit(String hint, String value) {
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setText(value);
        input.setHint(hint);
        input.setHintTextColor(MUTED);
        input.setTextColor(TEXT);
        input.setTextSize(15);
        input.setBackground(background(BG, BORDER, 12));
        pad(input, 13, 10);
        input.setSelectAllOnFocus(false);
        return input;
    }
    private void buildChrome() {
        header = row();
        pad(header, 16, 14);
        header.setBackgroundColor(PANEL);
        TextView logo = text("N", 25, TEXT, true);
        logo.setGravity(Gravity.CENTER);
        logo.setBackground(background(BLUE, 0, 13));
        header.addView(logo, new LinearLayout.LayoutParams(dp(44), dp(44)));
        LinearLayout titles = column();
        LinearLayout.LayoutParams titlesLp = new LinearLayout.LayoutParams(0, -2, 1);
        titlesLp.leftMargin = dp(12);
        headerTitle = text("NODERA", 19, TEXT, true);
        serverLabel = text("Мобильное управление", 11, MUTED, false);
        titles.addView(headerTitle);
        titles.addView(serverLabel);
        header.addView(titles, titlesLp);
        progress = new ProgressBar(this);
        progress.setIndeterminate(true);
        progress.setVisibility(View.GONE);
        header.addView(progress, new LinearLayout.LayoutParams(dp(25), dp(25)));
        root.addView(header);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        body = column();
        body.setPadding(0, dp(12), 0, dp(28));
        scroll.addView(body);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        HorizontalScrollView nav = new HorizontalScrollView(this);
        nav.setHorizontalScrollBarEnabled(false);
        nav.setBackgroundColor(PANEL);
        tabs = row();
        pad(tabs, 8, 10);
        nav.addView(tabs);
        root.addView(nav);
    }
    private void setBusy(boolean state) {
        busy = state;
        progress.setVisibility(state ? View.VISIBLE : View.GONE);
    }
    private void reset(String title) {
        headerTitle.setText(title);
        serverLabel.setText(origin.isEmpty() ? "Мобильное управление" : origin.replace("https://", ""));
        body.removeAllViews();
        tabs.removeAllViews();
    }
    private void nav() {
        tabs.removeAllViews();
        addNav("Файлы", "files", can("files.read"));
        addNav("Уведомления" + (unread > 0 ? " (" + unread + ")" : ""), "notifications", true);
        addNav("Запросы", "requests", can("devices.approve"));
        addNav("Пригласить", "invite", can("devices.invite") || can("devices.approve"));
        addNav("Устройства", "devices", can("devices.approve"));
        addNav("Сервер", "settings", true);
    }
    private void addNav(String name, String id, boolean allowed) {
        if (!allowed) return;
        Button b = button(name, tab.equals(id), () -> {
            if (id.equals("settings")) { tab = id; showSettings(); }
            else { tab = id; loadCurrent(false); }
        });
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, dp(42));
        lp.leftMargin = dp(5);
        tabs.addView(b, lp);
    }
    private boolean can(String permission) {
        JSONObject p = me.optJSONObject("permissions");
        return me.optBoolean("is_server_root") || (p != null && (p.optBoolean(permission) || p.optBoolean("*")));
    }
    private void styledDialog(AlertDialog dialog) {
        dialog.show();
        if (dialog.getWindow() != null) dialog.getWindow().setBackgroundDrawable(background(PANEL, BORDER, 18));
        if (dialog.getButton(AlertDialog.BUTTON_POSITIVE) != null) dialog.getButton(AlertDialog.BUTTON_POSITIVE).setTextColor(BLUE);
        if (dialog.getButton(AlertDialog.BUTTON_NEGATIVE) != null) dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setTextColor(MUTED);
    }
    private void message(String title, String detail) {
        styledDialog(new AlertDialog.Builder(this)
                .setTitle(title).setMessage(detail).setPositiveButton("Понятно", null).create());
    }
    private void confirm(String title, String detail, Runnable yes) {
        styledDialog(new AlertDialog.Builder(this).setTitle(title).setMessage(detail)
                .setPositiveButton("Подтвердить", (dialog, which) -> yes.run())
                .setNegativeButton("Отмена", null).create());
    }
    private void error(Exception e) {
        String detail = e.getMessage();
        if (e instanceof NoderaApi.ApiException) {
            int code = ((NoderaApi.ApiException) e).status;
            if (code == 403) detail = "Действие запрещено назначенным профилем или правилами доступа.";
            if (code == 401) detail = "Телефон ещё не одобрен или доступ отозван.";
        }
        message("NODERA · Ошибка", detail == null ? "Неизвестная ошибка" : detail);
    }
    private void task(Callable<JSONObject> work, Consumer<JSONObject> done) {
        if (busy) return;
        setBusy(true);
        worker.execute(() -> {
            try {
                JSONObject result = work.call();
                ui.post(() -> { setBusy(false); done.accept(result); });
            } catch (Exception e) {
                ui.post(() -> { setBusy(false); error(e); });
            }
        });
    }
    private static String inviteFromIntent(Intent intent) {
        if (intent == null) return "";
        if (Intent.ACTION_VIEW.equals(intent.getAction()) && intent.getData() != null) {
            return InviteLink.extract(intent.getData().toString());
        }
        if (Intent.ACTION_SEND.equals(intent.getAction()) && "text/plain".equals(intent.getType())) {
            return InviteLink.extract(intent.getStringExtra(Intent.EXTRA_TEXT));
        }
        return "";
    }
    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        String raw = inviteFromIntent(intent);
        if (!raw.isEmpty()) showSetup(raw, "Получено новое приглашение NODERA. Имя пользователя можно изменить.");
    }
    private void showSetup(String initial, String info) {
        api = null;
        pending = false;
        reset("Подключение");
        LinearLayout c = card();
        line(c, "Подключение по приглашению", 22, TEXT, true);
        gap(c, 10);
        line(c, "Вставьте ту же полную ссылку nodera://join?, которая используется на ПК. Адрес сервера и защищённое подключение считываются автоматически.", 14, MUTED, false);
        gap(c, 14);
        String linkPrefill = InviteLink.extract(initial);
        EditText invite = edit("Ссылка nodera://join?", linkPrefill);
        c.addView(invite);
        gap(c, 12);
        EditText name = edit("Ваше имя", getPreferences(MODE_PRIVATE).getString("user", ""));
        c.addView(name);
        gap(c, 8);
        line(c, "Имя остаётся отдельным полем, как в Windows. Название сервера из ссылки его не заменяет.", 12, MUTED, false);
        if (!linkPrefill.isEmpty()) {
            try {
                InviteLink parsed = InviteLink.parse(linkPrefill);
                if (!parsed.serverName.isEmpty()) {
                    gap(c, 12);
                    line(c, "Сервер: " + parsed.serverName, 14, TEXT, true);
                }
            } catch (Exception ignored) { /* Connection shows a detailed parse error. */ }
        }
        if (!info.isEmpty()) { gap(c, 12); line(c, info, 13, MUTED, false); }
        addButton(c, "Отправить запрос", true, () -> connect("", name.getText().toString(), invite.getText().toString()));
        gap(c, 16);
        line(c, "Уже подключали этот телефон? После перезапуска NODERA восстановит одобренное соединение. Доступ к файлам — только для просмотра метаданных.", 12, MUTED, false);
    }
    private void connect(String input, String user, String invitation) {
        final InviteLink link;
        final List<String> candidates;
        final String fingerprint;
        final String identityScope;
        final String token;
        final String name = user == null ? "" : user.trim();
        try {
            String complete = InviteLink.extract(invitation);
            if (complete.isEmpty()) complete = InviteLink.extract(input);
            if (!complete.isEmpty()) {
                link = InviteLink.parse(complete);
                candidates = link.controlOrigins;
                fingerprint = link.fingerprint;
                identityScope = link.identityScope();
                token = link.token;
                if (name.isEmpty()) throw new IllegalArgumentException("Введите имя пользователя.");
            } else {
                // Existing approved mobile identities can reconnect without another
                // one-time invitation. First enrollment requires the full link.
                if (!invitation.trim().isEmpty()) throw new IllegalArgumentException("Нужна полная ссылка NODERA, а не один токен.");
                link = null;
                String url = ServerAddress.mobileUrl(input);
                String endpoint = url.substring(0, url.length() - "/mobile/".length());
                String saved = getPreferences(MODE_PRIVATE).getString("server", "");
                if (!url.equals(saved)) throw new IllegalArgumentException("Для первого подключения вставьте полную ссылку от NODERA для ПК.");
                candidates = Collections.singletonList(endpoint);
                fingerprint = getPreferences(MODE_PRIVATE).getString("fingerprint", "");
                identityScope = getPreferences(MODE_PRIVATE).getString("identity_scope", "");
                token = "";
            }
        } catch (IllegalArgumentException e) { error(e); return; }
        reset("Подключение");
        LinearLayout c = card();
        line(c, "Соединение с NODERA", 20, TEXT, true);
        gap(c, 12);
        line(c, "Проверяем адреса из приглашения и TLS-сертификат сервера. Затем отправим запрос на одобрение…", 14, MUTED, false);
        setBusy(true);
        worker.execute(() -> {
            Exception lastError = null;
            for (String endpoint : candidates) {
                try {
                    SecureIdentity id = SecureIdentity.loadOrCreate(this, identityScope.isEmpty() ? endpoint : identityScope);
                    NoderaApi client = new NoderaApi(endpoint, id, fingerprint);
                    JSONObject health = client.publicGet("/healthz");
                    if (!"NODERA".equalsIgnoreCase(health.optString("product")))
                        throw new IllegalArgumentException("Адрес не принадлежит NODERA Server Root.");
                    if (link != null && !link.serverID.isEmpty()) {
                        JSONObject server = client.publicGet("/v1/server");
                        if (!link.serverID.equals(server.optString("server_id")))
                            throw new SecurityException("ID сервера не совпадает со ссылкой NODERA.");
                    }
                    boolean approved = true;
                    JSONObject account = null;
                    try { client.authenticate(); account = client.get("/v1/me"); }
                    catch (NoderaApi.ApiException ex) {
                        if (ex.status != 401 && ex.status != 403) throw ex;
                        approved = false;
                    }
                    if (!approved && !token.isEmpty()) {
                        JSONObject submission = id.joinSubmission(name);
                        client.publicPost("/v1/invitations/redeem", new JSONObject().put("token", token).put("submission", submission));
                    }
                    if (!approved && token.isEmpty() && !getPreferences(MODE_PRIVATE).getBoolean("join_pending", false))
                        throw new IllegalArgumentException("Устройство ещё не одобрено. Вставьте новое приглашение от администратора.");
                    final JSONObject finalAccount = account;
                    final boolean finalApproved = approved;
                    final String selected = endpoint;
                    ui.post(() -> {
                        identity = id; api = client; origin = selected; pending = !finalApproved;
                        getPreferences(MODE_PRIVATE).edit()
                                .putString("server", selected + "/mobile/")
                                .putString("user", name)
                                .putString("fingerprint", fingerprint)
                                .putString("identity_scope", identityScope)
                                .putBoolean("join_pending", !finalApproved)
                                .apply();
                        setBusy(false);
                        if (finalApproved) { me = finalAccount; tab = "files"; showDashboard(); }
                        else showPending();
                    });
                    return;
                } catch (SecurityException e) {
                    lastError = e;
                    // A wrong server ID is not a transient network failure.
                    break;
                } catch (Exception e) { lastError = e; }
            }
            Exception finalError = lastError == null ? new IllegalStateException("Сервер недоступен") : lastError;
            ui.post(() -> {
                setBusy(false);
                showSetup(link == null ? "" : invitation,
                        "Не удалось связаться с сервером. Проверьте Wi-Fi/VPN. Параметры Windows Tunnel в ссылке не означают, что Android автоматически включает VPN.");
                error(finalError);
            });
        });
    }
    private void showPending() {
        reset("Ожидание одобрения");
        LinearLayout c = card();
        line(c, "Запрос ожидает решения", 21, TEXT, true);
        gap(c, 12);
        line(c, "Администратор должен назначить профиль телефону. Проверка выполняется каждые 10 секунд, пока приложение открыто.", 14, MUTED, false);
        gap(c, 12);
        line(c, "ID устройства: " + (identity == null ? "" : identity.deviceID), 12, MUTED, false);
        addButton(c, "Проверить сейчас", true, () -> checkPending(false));
        addButton(c, "Сменить сервер", false, () -> showSetup("", ""));
    }
    private void checkPending(boolean silent) {
        if (api == null || busy) return;
        setBusy(true);
        worker.execute(() -> {
            try {
                api.authenticate();
                JSONObject account = api.get("/v1/me");
                ui.post(() -> { setBusy(false); pending = false; me = account; tab = "files";
                    getPreferences(MODE_PRIVATE).edit().putBoolean("join_pending", false).apply(); showDashboard(); });
            } catch (Exception e) {
                ui.post(() -> {
                    setBusy(false);
                    if (!silent && (!(e instanceof NoderaApi.ApiException) || ((NoderaApi.ApiException) e).status != 401)) error(e);
                });
            }
        });
    }
    private void showDashboard() {
        if (can("files.read")) tab = "files";
        else if (can("devices.approve")) tab = "requests";
        else tab = "notifications";
        loadCurrent(false);
    }
    private void loadCurrent(boolean silent) {
        if (api == null || busy) return;
        if (tab.equals("settings")) { showSettings(); return; }
        if (!silent) {
            reset("NODERA Mobile"); nav();
            LinearLayout c = card(); line(c, "Загрузка данных сервера…", 14, MUTED, false);
        }
        setBusy(true);
        worker.execute(() -> {
            try {
                JSONObject freshMe = api.get("/v1/me");
                JSONObject data;
                JSONArray nextProfiles = new JSONArray();
                switch (tab) {
                    case "files": data = api.get("/v1/mobile/files?path=" + URLEncoder.encode(folder, "UTF-8")); break;
                    case "notifications": data = api.get("/v1/notifications"); break;
                    case "requests":
                        data = api.get("/v1/join-requests");
                        nextProfiles = api.get("/v1/profiles").optJSONArray("profiles");
                        break;
                    case "devices": data = api.get("/v1/mobile/devices"); break;
                    default: data = new JSONObject(); break;
                }
                JSONArray p = nextProfiles == null ? new JSONArray() : nextProfiles;
                JSONObject response = data;
                ui.post(() -> {
                    setBusy(false); me = freshMe; profiles = p;
                    if (tab.equals("invite")) showInvites();
                    else if (tab.equals("files")) showFiles(response);
                    else if (tab.equals("notifications")) showNotifications(response);
                    else if (tab.equals("requests")) showRequests(response);
                    else if (tab.equals("devices")) showDevices(response);
                });
            } catch (Exception e) {
                ui.post(() -> { setBusy(false); if (!silent) error(e); });
            }
        });
    }
    private void showFiles(JSONObject data) {
        reset("Файлы · только просмотр"); nav();
        LinearLayout c = card();
        line(c, "Папка: " + folder, 15, TEXT, true);
        line(c, "Файлы находятся на Server Root. Скачивание и открытие недоступны.", 12, MUTED, false);
        if (!folder.equals("/")) addButton(c, "← Назад", false, () -> { folder = parent(folder); loadCurrent(false); });
        JSONArray files = data.optJSONArray("items");
        if (files == null || files.length() == 0) { gap(c, 16); line(c, "В этой папке нет доступных элементов", 14, MUTED, false); return; }
        for (int i = 0; i < files.length(); i++) {
            JSONObject f = files.optJSONObject(i);
            if (f == null) continue;
            LinearLayout item = card();
            boolean dir = f.optBoolean("is_dir");
            line(item, (dir ? "📁  " : "▤  ") + f.optString("name"), 16, TEXT, true);
            gap(item, 5);
            String size = dir ? "Папка" : readableSize(f.optLong("size"));
            line(item, size + " · " + f.optString("modified_at"), 12, MUTED, false);
            if (dir) addButton(item, "Открыть папку", false, () -> { folder = f.optString("logical_path", "/"); loadCurrent(false); });
            else addButton(item, "Сведения о файле", false, () -> message("Сведения", f.optString("name") + "\nРазмер: " + size + "\nИзменён: " + f.optString("modified_at") + "\n\nФайл нельзя открыть или скачать на телефон."));
            if (f.optBoolean("can_delete") || f.optBoolean("can_request_delete")) {
                boolean direct = f.optBoolean("can_delete");
                addButton(item, direct ? "Переместить в корзину" : "Запросить удаление", false,
                        () -> confirm(direct ? "Удаление файла" : "Запрос удаления",
                                (dir ? "Папка и её содержимое: " : "Файл: ") + f.optString("name") +
                                        (direct ? "\n\nПереместить в корзину сервера?" : "\n\nОтправить запрос администратору?"),
                                () -> trash(f.optString("file_id"))));
            }
        }
    }
    private static String parent(String path) {
        if (path == null || path.equals("/") || path.isEmpty()) return "/";
        int slash = path.lastIndexOf('/');
        return slash <= 0 ? "/" : path.substring(0, slash);
    }
    private static String readableSize(long bytes) {
        if (bytes < 1024) return bytes + " Б";
        if (bytes < 1024 * 1024) return String.format(java.util.Locale.ROOT, "%.1f КБ", bytes / 1024.0);
        if (bytes < 1024L * 1024 * 1024) return String.format(java.util.Locale.ROOT, "%.1f МБ", bytes / (1024.0 * 1024));
        return String.format(java.util.Locale.ROOT, "%.2f ГБ", bytes / (1024.0 * 1024 * 1024));
    }
    private void trash(String id) {
        task(() -> api.post("/v1/mobile/files/trash", new JSONObject().put("file_id", id)), result -> {
            if (result.optString("status").equals("approval_required")) message("Запрос отправлен", "Удаление будет выполнено после одобрения администратора.");
            else message("Перемещено в корзину", "Файл удалён из основной папки. Восстановление доступно на сервере.");
            loadCurrent(false);
        });
    }
    private void showNotifications(JSONObject data) {
        unread = data.optInt("unread");
        reset("Уведомления"); nav();
        JSONArray arr = data.optJSONArray("notifications");
        LinearLayout c = card();
        line(c, "Непрочитанных: " + data.optInt("unread"), 18, TEXT, true);
        if (arr == null || arr.length() == 0) { gap(c, 14); line(c, "Новых уведомлений нет", 14, MUTED, false); return; }
        for (int i = 0; i < arr.length(); i++) {
            JSONObject n = arr.optJSONObject(i); if (n == null) continue;
            LinearLayout item = card();
            boolean unread = n.optLong("read_at_unix_milli") == 0;
            line(item, (unread ? "●  " : "") + n.optString("title"), 16, unread ? TEXT : MUTED, true);
            gap(item, 6);
            line(item, n.optString("message"), 14, MUTED, false);
            if (unread) addButton(item, "Отметить прочитанным", false, () -> task(
                    () -> api.post("/v1/notifications/action", new JSONObject().put("id", n.optString("id")).put("action", "read")),
                    response -> loadCurrent(false)));
        }
    }
    private void showRequests(JSONObject data) {
        reset("Запросы на подключение"); nav();
        JSONArray arr = data.optJSONArray("requests");
        LinearLayout c = card();
        line(c, "Ожидают решения: " + (arr == null ? 0 : arr.length()), 18, TEXT, true);
        if (arr == null || arr.length() == 0) { gap(c, 14); line(c, "Новых запросов нет", 14, MUTED, false); return; }
        for (int i = 0; i < arr.length(); i++) {
            JSONObject req = arr.optJSONObject(i); if (req == null) continue;
            LinearLayout item = card();
            line(item, req.optString("device_name", "Устройство"), 17, TEXT, true);
            gap(item, 5);
            line(item, req.optString("user_name") + " · " + req.optString("client_kind", "desktop"), 13, MUTED, false);
            addButton(item, "Одобрить и назначить профиль", true, () -> selectProfile(req));
            addButton(item, "Отклонить", false, () -> confirm("Отклонить подключение?", req.optString("device_name"), () -> decision(req.optString("id"), "reject", "")));
        }
    }
    private void selectProfile(JSONObject request) {
        List<String> labels = new ArrayList<>(), ids = new ArrayList<>();
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject p = profiles.optJSONObject(i);
            if (p == null || p.optString("id").equals("root_admin")) continue;
            labels.add(p.optString("name", p.optString("id")));
            ids.add(p.optString("id"));
        }
        if (ids.isEmpty()) { message("Нет доступных профилей", "Создайте профиль на сервере NODERA."); return; }
        int[] selected = {Math.max(0, ids.indexOf("user"))};
        styledDialog(new AlertDialog.Builder(this).setTitle("Назначить профиль")
                .setSingleChoiceItems(labels.toArray(new String[0]), selected[0], (dialog, which) -> selected[0] = which)
                .setPositiveButton("Продолжить", (dialog, which) -> {
                    String id = ids.get(selected[0]);
                    confirm("Подтвердить подключение", request.optString("device_name") + "\nПрофиль: " + labels.get(selected[0]),
                            () -> decision(request.optString("id"), "approve", id));
                }).setNegativeButton("Отмена", null).create());
    }
    private void decision(String id, String action, String profile) {
        task(() -> api.post("/v1/join-requests/" + id + "/" + action,
                        action.equals("approve") ? new JSONObject().put("profile_id", profile) : new JSONObject()),
                response -> { message("Готово", action.equals("approve") ? "Подключение одобрено." : "Запрос отклонён."); loadCurrent(false); });
    }
    private void showInvites() {
        reset("Приглашения"); nav();
        LinearLayout c = card();
        line(c, "Пригласить пользователя", 21, TEXT, true);
        gap(c, 8);
        line(c, "Приглашение одноразовое. Права и профиль назначаются отдельно при одобрении запроса.", 14, MUTED, false);
        gap(c, 14);
        Spinner ttl = new Spinner(this);
        ttl.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, new String[]{"15 минут", "60 минут", "24 часа"}));
        c.addView(ttl);
        addButton(c, "Создать приглашение", true, () -> createInvite(new int[]{15, 60, 1440}[ttl.getSelectedItemPosition()]));
        if (!generatedInvite.isEmpty()) {
            gap(c, 16);
            line(c, "Приглашение готово", 16, TEXT, true);
            gap(c, 6);
            line(c, generatedInviteNote, 12, MUTED, false);
            addButton(c, "Поделиться ссылкой", true, this::shareInvite);
        }
    }
    private void createInvite(int minutes) {
        task(() -> {
            JSONObject body = new JSONObject().put("role", "employee").put("ttl_minutes", minutes).put("known_control_url", origin);
            return api.post("/v1/invitations/bootstrap", body);
        }, result -> {
            generatedInvite = result.optString("link");
            if (!InviteLink.looksLikeLink(generatedInvite)) {
                message("NODERA", "Сервер не вернул полную ссылку подключения.");
                return;
            }
            generatedInviteNote = result.optString("remote_detail", "Проверьте доступность сервера у получателя.");
            showInvites();
        });
    }
    private void shareInvite() {
        if (generatedInvite.isEmpty()) return;
        Intent send = new Intent(Intent.ACTION_SEND);
        send.setType("text/plain");
        send.putExtra(Intent.EXTRA_TEXT, "Приглашение NODERA:\n" + generatedInvite + "\n" + generatedInviteNote);
        startActivity(Intent.createChooser(send, "Отправить приглашение"));
    }
    private void showDevices(JSONObject data) {
        reset("Устройства"); nav();
        JSONArray arr = data.optJSONArray("devices");
        LinearLayout c = card();
        line(c, "Подключённые устройства", 18, TEXT, true);
        if (arr == null || arr.length() == 0) { gap(c, 12); line(c, "Нет доступных устройств", 14, MUTED, false); return; }
        for (int i = 0; i < arr.length(); i++) {
            JSONObject d = arr.optJSONObject(i); if (d == null) continue;
            LinearLayout item = card();
            line(item, d.optString("device_name", "Устройство"), 16, TEXT, true);
            gap(item, 4);
            line(item, d.optString("user_name") + " · " + d.optString("profile_id") + " · " + d.optString("status"), 12, MUTED, false);
        }
    }
    private void showSettings() {
        reset("Сервер и доступ"); nav();
        LinearLayout c = card();
        line(c, "Сервер", 20, TEXT, true);
        gap(c, 8);
        line(c, origin, 13, MUTED, false);
        gap(c, 12);
        line(c, "Профиль: " + me.optString("profile_name"), 15, TEXT, true);
        line(c, "ID телефона: " + (identity == null ? "" : identity.deviceID), 12, MUTED, false);
        gap(c, 12);
        line(c, "Файлы остаются на сервере. Нельзя скачивать, открывать, загружать или редактировать их с телефона.", 13, MUTED, false);
        addButton(c, "Сменить сервер", false, () -> confirm("Сменить сервер?", "Для другого сервера будет создана отдельная идентичность и потребуется одобрение.", () -> {
            api = null; identity = null; origin = ""; me = new JSONObject(); folder = "/";
            getPreferences(MODE_PRIVATE).edit().remove("server").remove("fingerprint").remove("identity_scope").remove("join_pending").apply();
            showSetup("", "");
        }));
    }
    @Override public void onBackPressed() {
        if (pending) { showSetup("", ""); return; }
        if (tab.equals("files") && !folder.equals("/")) { folder = parent(folder); loadCurrent(false); return; }
        super.onBackPressed();
    }
    @Override protected void onResume() {
        super.onResume(); active = true; ui.removeCallbacks(poll); ui.postDelayed(poll, POLL_MS);
    }
    @Override protected void onPause() {
        active = false; ui.removeCallbacks(poll); super.onPause();
    }
    @Override protected void onDestroy() {
        active = false; ui.removeCallbacks(poll); worker.shutdownNow(); super.onDestroy();
    }
}
