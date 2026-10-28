package com.domokrat.nodera.mobile;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.security.cert.X509Certificate;
import java.util.Locale;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSession;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import javax.net.ssl.SSLSocketFactory;
import java.nio.charset.StandardCharsets;

/** HTTPS JSON client. Tokens live only in RAM and are renewed by device-bound signatures. */
public final class NoderaApi {
    public static final class ApiException extends IOException {
        public final int status;
        ApiException(int status, String message) { super(message); this.status = status; }
    }
    private final String origin;
    private final SecureIdentity identity;
    private final String pinnedFingerprint;
    private final SSLSocketFactory pinnedFactory;
    private String token;
    private long expires;

    public NoderaApi(String origin, SecureIdentity identity) { this(origin, identity, ""); }
    public NoderaApi(String origin, SecureIdentity identity, String fingerprint) {
        if (!origin.startsWith("https://") || origin.endsWith("/")) throw new IllegalArgumentException("Invalid origin");
        String pin = fingerprint == null ? "" : fingerprint.trim().toLowerCase(Locale.ROOT);
        if (!pin.isEmpty() && !pin.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("Недействительный TLS-отпечаток.");
        this.origin = origin;
        this.identity = identity;
        this.pinnedFingerprint = pin;
        this.pinnedFactory = pin.isEmpty() ? null : createPinnedFactory(pin);
    }
    /** Pin the exact server certificate from Windows' invitation. A matching
     * pinned certificate is trusted even if the private server uses a self-signed
     * identity or its LAN IP is not present in the X.509 SAN.
     */
    private static SSLSocketFactory createPinnedFactory(String pin) {
        try {
            X509TrustManager trust = new X509TrustManager() {
                @Override public void checkClientTrusted(X509Certificate[] chain, String authType) throws java.security.cert.CertificateException {
                    throw new java.security.cert.CertificateException("NODERA client certs not supported");
                }
                @Override public void checkServerTrusted(X509Certificate[] chain, String authType) throws java.security.cert.CertificateException {
                    if (chain == null || chain.length == 0 || !matchesPin(chain[0], pin))
                        throw new java.security.cert.CertificateException("Отпечаток TLS-сертификата не совпадает со ссылкой NODERA.");
                    chain[0].checkValidity();
                }
                @Override public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
            };
            SSLContext context = SSLContext.getInstance("TLS");
            context.init(null, new TrustManager[]{trust}, null);
            return context.getSocketFactory();
        } catch (Exception e) { throw new IllegalStateException("Не удалось настроить защищённое соединение", e); }
    }
    private static boolean matchesPin(X509Certificate certificate, String pin) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(certificate.getEncoded());
            byte[] expected = new byte[32];
            for (int i = 0; i < 32; i++) expected[i] = (byte) Integer.parseInt(pin.substring(i * 2, i * 2 + 2), 16);
            return MessageDigest.isEqual(digest, expected);
        } catch (Exception e) { return false; }
    }
    public String origin() { return origin; }
    public synchronized JSONObject get(String path) throws Exception { return authorized("GET", path, null); }
    public synchronized JSONObject post(String path, JSONObject body) throws Exception { return authorized("POST", path, body); }
    public synchronized JSONObject publicPost(String path, JSONObject body) throws Exception { return call("POST", path, body, null); }
    public synchronized JSONObject publicGet(String path) throws Exception { return call("GET", path, null, null); }

    public synchronized void authenticate() throws Exception {
        JSONObject request = new JSONObject().put("device_id", identity.deviceID);
        JSONObject challenge = call("POST", "/v1/auth/challenge", request, null);
        byte[] message = Protocol.challenge(challenge.getString("id"), challenge.getString("device_id"), challenge.getString("nonce"), challenge.getString("server_id"));
        JSONObject proof = new JSONObject().put("challenge_id", challenge.getString("id"))
                .put("signature_base64", SecureIdentity.base64(identity.sign(message)));
        JSONObject result = call("POST", "/v1/auth/verify", proof, null);
        token = result.getString("access_token");
        expires = result.getLong("expires_unix_milli");
    }
    private JSONObject authorized(String method, String path, JSONObject body) throws Exception {
        if (token == null || System.currentTimeMillis() >= expires - 60_000) authenticate();
        try { return call(method, path, body, token); }
        catch (ApiException ex) {
            if (ex.status != 401) throw ex;
            token = null;
            authenticate();
            return call(method, path, body, token);
        }
    }
    private JSONObject call(String method, String path, JSONObject body, String bearer) throws Exception {
        if (!path.startsWith("/v1/") && !path.equals("/healthz")) throw new SecurityException("Unsupported API path");
        if (path.contains("#") || path.contains("\\") || path.contains("\r") || path.contains("\n") || path.startsWith("//")) throw new SecurityException("Invalid API path");
        HttpURLConnection connection = (HttpURLConnection) new URL(origin + path).openConnection();
        if (pinnedFactory != null) {
            HttpsURLConnection https = (HttpsURLConnection) connection;
            https.setSSLSocketFactory(pinnedFactory);
            // Only a matching exact certificate pin is accepted; no global SSL bypass.
            https.setHostnameVerifier((hostname, session) -> {
                try {
                    java.security.cert.Certificate[] peer = session.getPeerCertificates();
                    return peer.length > 0 && peer[0] instanceof X509Certificate &&
                            matchesPin((X509Certificate) peer[0], pinnedFingerprint);
                } catch (Exception e) { return false; }
            });
        }
        connection.setInstanceFollowRedirects(false);
        connection.setRequestMethod(method);
        connection.setConnectTimeout(8000);
        connection.setReadTimeout(12000);
        connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("Cache-Control", "no-store");
        if (bearer != null) connection.setRequestProperty("Authorization", "Bearer " + bearer);
        try {
            if (body != null) {
                byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (OutputStream out = connection.getOutputStream()) { out.write(bytes); }
            }
            int code = connection.getResponseCode();
            if (code >= 300 && code < 400) throw new ApiException(code, "Перенаправление сервера заблокировано.");
            InputStream input = code < 400 ? connection.getInputStream() : connection.getErrorStream();
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            if (input != null) {
                try (InputStream in = input) {
                    byte[] buffer = new byte[4096]; int n;
                    while ((n = in.read(buffer)) != -1) {
                        if (out.size() + n > 2_000_000) throw new IOException("Ответ сервера слишком большой");
                        out.write(buffer, 0, n);
                    }
                }
            }
            JSONObject result = out.size() == 0 ? new JSONObject() : new JSONObject(out.toString("UTF-8"));
            if (code >= 400) throw new ApiException(code, result.optString("error", "HTTP " + code));
            return result;
        } finally { connection.disconnect(); }
    }
}
