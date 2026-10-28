package com.domokrat.nodera.mobile;

import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Reads the identical nodera://join? bootstrap link used by the Windows client.
 * Tunnel/SMB/relay secrets remain in the link, but the mobile client never uses
 * or persists them: only HTTPS control endpoints are needed for management.
 */
public final class InviteLink {
    public final String token;
    public final String fingerprint;
    public final String serverID;
    public final String serverName;
    public final String shareName;
    public final String drive;
    public final List<String> controlOrigins;
    private InviteLink(Map<String, List<String>> params) {
        token = first(params, "token");
        fingerprint = first(params, "fp").toLowerCase(Locale.ROOT);
        serverID = first(params, "sid");
        serverName = first(params, "name");
        shareName = first(params, "share");
        drive = first(params, "drive");
        if (token.isEmpty() || !fingerprint.matches("[a-f0-9]{64}")) {
            throw new IllegalArgumentException("Приглашение не содержит действительный токен и TLS-отпечаток сервера.");
        }
        String server = first(params, "server");
        if (server.isEmpty()) throw new IllegalArgumentException("В приглашении отсутствует адрес сервера.");
        LinkedHashSet<String> endpoints = new LinkedHashSet<>();
        for (String raw : new String[]{server, first(params, "lan"), first(params, "radmin")}) {
            if (!raw.isEmpty()) endpoints.add(normalize(raw));
        }
        for (String raw : params.getOrDefault("alt", Collections.emptyList())) {
            if (!raw.isEmpty()) endpoints.add(normalize(raw));
        }
        if (endpoints.size() > 16) throw new IllegalArgumentException("Слишком много адресов в приглашении.");
        controlOrigins = Collections.unmodifiableList(new ArrayList<>(endpoints));
    }
    public String identityScope() { return !serverID.isEmpty() ? "server:" + serverID + ":" + fingerprint : "fingerprint:" + fingerprint; }
    private static String normalize(String v) {
        String mobile = ServerAddress.mobileUrl(v);
        return mobile.substring(0, mobile.length() - "/mobile/".length());
    }
    private static String first(Map<String, List<String>> map, String key) {
        List<String> values = map.get(key);
        return values == null || values.isEmpty() ? "" : values.get(0);
    }
    private static Map<String, List<String>> params(String query) {
        Map<String, List<String>> out = new LinkedHashMap<>();
        for (String item : query.split("&", -1)) {
            if (item.isEmpty()) continue;
            int eq = item.indexOf('=');
            if (eq < 0) throw new IllegalArgumentException("Некорректный параметр в приглашении.");
            try {
                String key = URLDecoder.decode(item.substring(0, eq), StandardCharsets.UTF_8.name());
                String value = URLDecoder.decode(item.substring(eq + 1), StandardCharsets.UTF_8.name());
                if (key.length() > 48 || value.length() > 8192) throw new IllegalArgumentException("Слишком длинный параметр приглашения.");
                out.computeIfAbsent(key, k -> new ArrayList<>()).add(value);
            } catch (java.io.UnsupportedEncodingException e) { throw new IllegalStateException(e); }
            catch (IllegalArgumentException e) { throw new IllegalArgumentException("Некорректная кодировка приглашения.", e); }
        }
        // Prevent an ambiguous token, pin or server selection.
        for (String key : new String[]{"server", "fp", "token", "sid"}) {
            if (out.containsKey(key) && out.get(key).size() != 1) throw new IllegalArgumentException("Дублирующийся параметр " + key);
        }
        return out;
    }
    public static boolean looksLikeLink(String value) {
        return value != null && value.trim().toLowerCase(Locale.ROOT).startsWith("nodera://join?");
    }
    /** Accept the same link when opened by a browser, pasted, or sent via Share. */
    public static String extract(String text) {
        if (text == null) return "";
        int index = text.toLowerCase(Locale.ROOT).indexOf("nodera://join?");
        if (index < 0) return "";
        int end = index;
        while (end < text.length()) {
            char c = text.charAt(end);
            if (Character.isWhitespace(c) || c == '<' || c == '>' || c == '\"' || c == '\'') break;
            end++;
        }
        return text.substring(index, end);
    }
    public static InviteLink parse(String text) {
        String raw = extract(text);
        if (raw.isEmpty() || raw.length() > 32768) throw new IllegalArgumentException("Вставьте полную ссылку nodera://join? из NODERA для ПК.");
        final URI uri;
        try { uri = URI.create(raw); } catch (IllegalArgumentException e) { throw new IllegalArgumentException("Некорректный формат ссылки NODERA.", e); }
        if (!"nodera".equalsIgnoreCase(uri.getScheme()) || !"join".equalsIgnoreCase(uri.getHost()) ||
                uri.getRawFragment() != null || uri.getRawQuery() == null) {
            throw new IllegalArgumentException("Это не ссылка подключения NODERA.");
        }
        return new InviteLink(params(uri.getRawQuery()));
    }
}
