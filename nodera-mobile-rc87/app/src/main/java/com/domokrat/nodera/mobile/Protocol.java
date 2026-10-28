package com.domokrat.nodera.mobile;

import java.nio.charset.StandardCharsets;

/** Byte-for-byte compatible with NODERA server Ed25519 signed messages. */
public final class Protocol {
    private Protocol() {}
    public static byte[] join(String id, String device, String user, String pub, String nonce) {
        return String.join("\n", "NODERA-JOIN-MOBILE-V1", id, device, user, "", pub, nonce, "mobile")
                .getBytes(StandardCharsets.UTF_8);
    }
    public static byte[] challenge(String challengeID, String deviceID, String nonce, String serverID) {
        return String.join("\n", "NODERA-AUTH-V1", challengeID, deviceID, nonce, serverID)
                .getBytes(StandardCharsets.UTF_8);
    }
}
