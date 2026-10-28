package com.domokrat.nodera.mobile;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import com.google.crypto.tink.subtle.Ed25519Sign;

import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.SecureRandom;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Per-server Ed25519 identity encrypted at rest using an Android Keystore AES-GCM key. */
public final class SecureIdentity {
    private static final String KEY_ALIAS = "nodera_mobile_identity_aes_v1";
    private static final String PREF = "nodera_native_identity_v1";
    private static final String ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";
    public final String deviceID;
    public final String publicKey;
    private final byte[] seed;

    private SecureIdentity(String id, String publicKey, byte[] seed) {
        this.deviceID = id;
        this.publicKey = publicKey;
        this.seed = seed;
    }
    public static String base64(byte[] data) {
        return Base64.encodeToString(data, Base64.NO_WRAP | Base64.NO_PADDING);
    }
    public static String base64url(byte[] data) {
        return Base64.encodeToString(data, Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
    }
    private static SecretKey aesKey() throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if (store.containsAlias(KEY_ALIAS)) return ((KeyStore.SecretKeyEntry) store.getEntry(KEY_ALIAS, null)).getSecretKey();
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true).build());
        return generator.generateKey();
    }
    private static byte[] encrypt(byte[] plain) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, aesKey());
        byte[] iv = cipher.getIV();
        byte[] ct = cipher.doFinal(plain);
        byte[] out = new byte[iv.length + ct.length];
        System.arraycopy(iv, 0, out, 0, iv.length);
        System.arraycopy(ct, 0, out, iv.length, ct.length);
        return out;
    }
    private static byte[] decrypt(byte[] encrypted) throws Exception {
        if (encrypted.length < 12 + 16) throw new SecurityException("Invalid identity payload");
        byte[] iv = new byte[12];
        System.arraycopy(encrypted, 0, iv, 0, 12);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, aesKey(), new GCMParameterSpec(128, iv));
        return cipher.doFinal(encrypted, 12, encrypted.length - 12);
    }
    private static String newDeviceID() {
        SecureRandom random = new SecureRandom();
        StringBuilder s = new StringBuilder();
        for (int i = 0; i < 12; i++) {
            if (i == 4 || i == 8) s.append('-');
            s.append(ALPHABET.charAt(random.nextInt(ALPHABET.length())));
        }
        return s.toString();
    }
    public static SecureIdentity loadOrCreate(Context context, String origin) throws Exception {
        return loadOrCreate(context, origin, "");
    }
    public static SecureIdentity loadOrCreate(Context context, String origin, String serverScope) throws Exception {
        SharedPreferences prefs = context.getSharedPreferences(PREF, Context.MODE_PRIVATE);
        String boundOrigin = prefs.getString("origin", "");
        String boundScope = prefs.getString("scope", "");
        String encrypted = prefs.getString("identity", "");
        // The same approved phone keeps one identity across primary/LAN/VPN
        // endpoints of one server. Do not reuse it across different servers.
        if (!encrypted.isEmpty() && (origin.equals(boundOrigin) ||
                (!serverScope.isEmpty() && serverScope.equals(boundScope)))) {
            // Never silently rotate an existing key: it would break server approval.
            JSONObject data = new JSONObject(new String(decrypt(Base64.decode(encrypted, Base64.DEFAULT)), StandardCharsets.UTF_8));
            return new SecureIdentity(data.getString("device_id"), data.getString("public_key"), Base64.decode(data.getString("seed"), Base64.DEFAULT));
        }
        Ed25519Sign.KeyPair pair = Ed25519Sign.KeyPair.newKeyPair();
        SecureIdentity result = new SecureIdentity(newDeviceID(), base64(pair.getPublicKey()), pair.getPrivateKey());
        JSONObject data = new JSONObject();
        data.put("device_id", result.deviceID);
        data.put("public_key", result.publicKey);
        data.put("seed", base64(result.seed));
        String sealed = base64(encrypt(data.toString().getBytes(StandardCharsets.UTF_8)));
        if (!prefs.edit().putString("origin", origin).putString("scope", serverScope).putString("identity", sealed).commit()) {
            throw new IllegalStateException("Cannot save device identity");
        }
        return result;
    }
    public byte[] sign(byte[] message) throws Exception {
        return new Ed25519Sign(seed).sign(message);
    }
    public JSONObject joinSubmission(String userName) throws Exception {
        String nonce = base64url(randomBytes(24));
        String deviceName = "NODERA Android";
        JSONObject obj = new JSONObject();
        obj.put("device_id", deviceID);
        obj.put("device_name", deviceName);
        obj.put("user_name", userName);
        obj.put("client_kind", "mobile");
        obj.put("public_key_base64", publicKey);
        obj.put("nonce_base64", nonce);
        obj.put("signature_base64", base64(sign(Protocol.join(deviceID, deviceName, userName, publicKey, nonce))));
        return obj;
    }
    private static byte[] randomBytes(int n) {
        byte[] b = new byte[n]; new SecureRandom().nextBytes(b); return b;
    }
}
