package com.domokrat.nodera.mobile;

import org.junit.Test;
import static org.junit.Assert.*;

public final class InviteLinkTest {
    private static final String FP = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    private static final String FULL = "nodera://join?server=https%3A%2F%2Fnodera.example%3A8787&lan=https%3A%2F%2F192.168.10.2%3A8787&" +
            "radmin=https%3A%2F%2F10.4.0.2%3A8787&alt=https%3A%2F%2Falt.example%3A8787&" +
            "token=abcdef&fp=" + FP + "&sid=srv-42&name=Office+Server&drive=V%3A&share=Projects&" +
            "tcsk=privatevpnkey&tspk=servervpnkey&tep=remote.example%3A51888";
    @Test public void parsesIdenticalWindowsInvitationWithoutLosingName() {
        InviteLink link = InviteLink.parse(FULL);
        assertEquals("Office Server", link.serverName);
        assertEquals("srv-42", link.serverID);
        assertEquals("abcdef", link.token);
        assertEquals(FP, link.fingerprint);
        assertEquals("V:", link.drive);
        assertEquals("Projects", link.shareName);
        assertEquals(4, link.controlOrigins.size());
        assertEquals("https://nodera.example:8787", link.controlOrigins.get(0));
        assertEquals("https://192.168.10.2:8787", link.controlOrigins.get(1));
        assertEquals("https://10.4.0.2:8787", link.controlOrigins.get(2));
        assertEquals("https://alt.example:8787", link.controlOrigins.get(3));
        assertFalse(link.identityScope().contains("abcdef"));
        assertFalse(link.identityScope().contains("privatevpnkey"));
    }
    @Test public void acceptsSharedText() {
        assertEquals("abcdef", InviteLink.parse("Приглашение NODERA:\n" + FULL + "\nПодключиться").token);
    }
    @Test public void rejectsIncompleteOrUnsafeInvitations() {
        String[] invalid = {"nodera://join?token=abc", "nodera://join?server=http%3A%2F%2Fevil&token=abc&fp=" + FP,
                "nodera://join?server=https%3A%2F%2Fok.example&token=abc&fp=xyz",
                FULL + "&token=other", "https://example.com/?token=abc"};
        for (String raw : invalid) {
            assertThrows(raw, IllegalArgumentException.class, () -> InviteLink.parse(raw));
        }
    }
}
