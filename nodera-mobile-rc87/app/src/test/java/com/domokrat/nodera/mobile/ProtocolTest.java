package com.domokrat.nodera.mobile;

import org.junit.Test;
import java.nio.charset.StandardCharsets;
import static org.junit.Assert.assertEquals;

public class ProtocolTest {
    @Test public void mobileJoinSignatureDomainMatchesServer() {
        assertEquals("NODERA-JOIN-MOBILE-V1\nABCD-EFGH-JKLM\nNODERA Android\nUser\n\npub\nnonce\nmobile",
                new String(Protocol.join("ABCD-EFGH-JKLM", "NODERA Android", "User", "pub", "nonce"), StandardCharsets.UTF_8));
    }
    @Test public void challengeSignatureDomainMatchesServer() {
        assertEquals("NODERA-AUTH-V1\nch_1\nABCD-EFGH-JKLM\nnonce\nsrv_1",
                new String(Protocol.challenge("ch_1", "ABCD-EFGH-JKLM", "nonce", "srv_1"), StandardCharsets.UTF_8));
    }
}
