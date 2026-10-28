package com.domokrat.nodera.mobile;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;

/** Strict same-origin server address validation; no HTTP or embedded credentials. */
public final class ServerAddress {
    private ServerAddress() {}

    public static String mobileUrl(String input) {
        if (input == null || input.trim().isEmpty()) {
            throw new IllegalArgumentException("Введите HTTPS-адрес сервера NODERA.");
        }
        final String value = input.trim();
        if (value.length() > 2048 || value.indexOf('\\') >= 0 || containsControl(value)) {
            throw new IllegalArgumentException("Адрес сервера содержит недопустимые символы.");
        }
        final URI uri;
        try {
            uri = new URI(value);
        } catch (URISyntaxException e) {
            throw new IllegalArgumentException("Неверный формат адреса сервера.", e);
        }
        if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null ||
                uri.getRawUserInfo() != null || uri.getRawQuery() != null || uri.getRawFragment() != null ||
                uri.getPort() > 65535 || uri.getPort() == 0) {
            throw new IllegalArgumentException("Используйте HTTPS-адрес без логина, пароля и параметров.");
        }
        final String path = uri.getRawPath();
        if (path != null && !path.isEmpty() && !path.equals("/") &&
                !path.equals("/mobile") && !path.equals("/mobile/")) {
            throw new IllegalArgumentException("Укажите адрес сервера или путь /mobile/.");
        }
        String host = uri.getHost().toLowerCase(Locale.ROOT);
        // java.net.URI encloses IPv6 literals in brackets in some JDKs.
        if (host.contains(":") && !host.startsWith("[")) host = "[" + host + "]";
        return "https://" + host + (uri.getPort() >= 0 ? ":" + uri.getPort() : "") + "/mobile/";
    }

    private static boolean containsControl(String text) {
        for (int i = 0; i < text.length(); i++) {
            if (Character.isISOControl(text.charAt(i))) return true;
        }
        return false;
    }
}
