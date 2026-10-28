package com.domokrat.nodera.mobile;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

public final class ServerAddressTest {
    @Test public void acceptsSecureOrigin() {
        assertEquals("https://nodera.example:8787/mobile/", ServerAddress.mobileUrl("https://NODERA.EXAMPLE:8787"));
        assertEquals("https://nodera.example/mobile/", ServerAddress.mobileUrl("https://nodera.example/mobile/"));
        assertEquals("https://192.168.1.20:8787/mobile/", ServerAddress.mobileUrl("https://192.168.1.20:8787/"));
    }
    @Test public void rejectsInsecureOrUnsafeUrl() {
        for (String bad : new String[]{"http://nodera.example", "https://user:pass@nodera.example", "https://nodera.example/path", "https://nodera.example/?token=abc", "javascript:alert(1)", "https://nodera.example:99999", "https://nodera.example\\evil", ""}) {
            assertThrows("Should reject: " + bad, IllegalArgumentException.class, () -> ServerAddress.mobileUrl(bad));
        }
    }
}
