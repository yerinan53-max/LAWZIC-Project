package com.lawzic.api.auth;

import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Base64;

import static org.springframework.http.HttpStatus.BAD_REQUEST;

@Service
@RequiredArgsConstructor
public class AccountRecoveryService {
    private static final Logger log = LoggerFactory.getLogger(AccountRecoveryService.class);
    private static final SecureRandom RANDOM = new SecureRandom();
    private final UserRepository users;
    private final PasswordResetTokenRepository tokens;
    private final AccountMailService mail;
    private final PasswordEncoder passwordEncoder;

    public void sendLoginId(String name, String email) {
        users.findByEmail(normalize(email))
                .filter(user -> user.getName().equals(name == null ? "" : name.trim()))
                .ifPresent(user -> {
                    try {
                        mail.sendLoginId(user.getEmail(), user.getEmail());
                    } catch (RuntimeException exception) {
                        log.error("가입 이메일 안내 메일 발송 실패: {}", user.getEmail(), exception);
                    }
                });
    }

    @Transactional
    public void requestPasswordReset(String email) {
        users.findByEmail(normalize(email)).ifPresent(user -> {
            tokens.deleteAllByUserEmail(user.getEmail());
            String rawToken = newToken();
            PasswordResetToken saved = tokens.save(new PasswordResetToken(
                    user, sha256(rawToken), Instant.now().plus(30, ChronoUnit.MINUTES)));
            try {
                mail.sendPasswordReset(user.getEmail(), rawToken);
            } catch (RuntimeException exception) {
                tokens.delete(saved);
                log.error("비밀번호 재설정 메일 발송 실패: {}", user.getEmail(), exception);
            }
        });
    }

    @Transactional
    public void resetPassword(String rawToken, String newPassword) {
        if (newPassword == null || newPassword.length() < 8 || newPassword.length() > 72) {
            throw new ResponseStatusException(BAD_REQUEST, "새 비밀번호는 8자 이상 72자 이하로 입력하세요.");
        }
        PasswordResetToken token = tokens.findByTokenHash(sha256(rawToken == null ? "" : rawToken))
                .orElseThrow(() -> new ResponseStatusException(BAD_REQUEST, "유효하지 않은 재설정 링크입니다."));
        if (!token.isUsable(Instant.now())) {
            throw new ResponseStatusException(BAD_REQUEST, "재설정 링크가 만료되었거나 이미 사용되었습니다.");
        }
        token.getUser().updatePassword(passwordEncoder.encode(newPassword));
        token.markUsed();
    }

    private String normalize(String email) {
        return email == null ? "" : email.trim().toLowerCase();
    }

    private String newToken() {
        byte[] bytes = new byte[32];
        RANDOM.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        }
    }
}
