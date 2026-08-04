package com.lawzic.api.auth;

import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Instant;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AccountRecoveryServiceTests {
    @Mock UserRepository users;
    @Mock PasswordResetTokenRepository tokens;
    @Mock AccountMailService mail;
    @Mock PasswordEncoder passwordEncoder;

    @Test
    void storesOnlyHashedResetCodeAndSendsSixDigitCodeByEmail() {
        User user = new User("owner@example.com", "old-hash", "사용자");
        when(users.findByEmail("owner@example.com")).thenReturn(Optional.of(user));
        when(tokens.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        AccountRecoveryService service = new AccountRecoveryService(users, tokens, mail, passwordEncoder);

        service.requestPasswordReset("OWNER@example.com");

        ArgumentCaptor<PasswordResetToken> stored = ArgumentCaptor.forClass(PasswordResetToken.class);
        ArgumentCaptor<String> raw = ArgumentCaptor.forClass(String.class);
        verify(tokens).save(stored.capture());
        verify(mail).sendPasswordReset(eq("owner@example.com"), raw.capture());
        assertEquals(64, stored.getValue().getTokenHash().length());
        assertNotEquals(raw.getValue(), stored.getValue().getTokenHash());
        assertTrue(raw.getValue().matches("\\d{6}"));
        assertTrue(stored.getValue().getExpiresAt().isAfter(Instant.now()));
    }

    @Test
    void consumesValidTokenAndChangesPassword() {
        User user = new User("owner@example.com", "old-hash", "사용자");
        PasswordResetToken token = new PasswordResetToken(user, "stored-hash", Instant.now().plusSeconds(60));
        when(tokens.findTopByUserEmailOrderByCreatedAtDesc("owner@example.com")).thenReturn(Optional.of(token));
        when(passwordEncoder.encode("new-password")).thenReturn("new-hash");
        AccountRecoveryService service = new AccountRecoveryService(users, tokens, mail, passwordEncoder);

        ReflectionTestUtils.setField(token, "tokenHash", sha256("123456"));
        service.resetPassword("owner@example.com", "123456", "new-password");

        assertEquals("new-hash", user.getPasswordHash());
        assertNotNull(token.getUsedAt());
    }

    private String sha256(String value) {
        try {
            return java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
        } catch (java.security.NoSuchAlgorithmException exception) {
            throw new IllegalStateException(exception);
        }
    }

    @Test
    void unknownEmailDoesNotRevealAccountOrSendMail() {
        when(users.findByEmail("missing@example.com")).thenReturn(Optional.empty());
        AccountRecoveryService service = new AccountRecoveryService(users, tokens, mail, passwordEncoder);

        service.requestPasswordReset("missing@example.com");

        verifyNoInteractions(mail, tokens);
    }
}
