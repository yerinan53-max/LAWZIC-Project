package com.lawzic.api.auth;

import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;

@Service
@RequiredArgsConstructor
public class OAuthLoginService {
    private static final SecureRandom RANDOM = new SecureRandom();
    private final UserRepository users;
    private final SocialIdentityRepository identities;
    private final OAuthLoginTicketRepository tickets;
    private final PasswordEncoder passwordEncoder;

    @Transactional
    public String issueTicket(String provider, String providerUserId, String email, String name) {
        SocialIdentity identity = identities.findByProviderAndProviderUserId(provider, providerUserId).orElse(null);
        User user = identity == null ? null : identity.getUser();
        boolean linkingRequired = false;
        boolean consentRequired = false;
        if (user == null) {
            User sameEmail = users.findByEmail(email).orElse(null);
            if (sameEmail != null) {
                linkingRequired = true;
            } else {
                consentRequired = true;
            }
        }
        String raw = randomToken();
        tickets.save(new OAuthLoginTicket(hash(raw), provider, providerUserId, email, name,
                user, linkingRequired, consentRequired, Instant.now().plusSeconds(120)));
        return raw;
    }

    @Transactional(readOnly = true)
    public TicketStatus inspect(String rawTicket) {
        OAuthLoginTicket ticket = valid(rawTicket);
        return new TicketStatus(ticket.isLinkingRequired(), ticket.isConsentRequired(),
                ticket.getProvider(), mask(ticket.getEmail()));
    }

    @Transactional
    public User exchange(String rawTicket) {
        OAuthLoginTicket ticket = valid(rawTicket);
        if (ticket.isLinkingRequired() || ticket.isConsentRequired() || ticket.getUser() == null) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "계정 연결 또는 필수 동의가 필요합니다.");
        }
        ticket.use();
        return ticket.getUser();
    }

    @Transactional
    public User link(String rawTicket, String email, String password) {
        OAuthLoginTicket ticket = valid(rawTicket);
        if (!ticket.isLinkingRequired()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "계정 연결이 필요하지 않은 요청입니다.");
        }
        User user = users.findByEmail(email == null ? "" : email.trim().toLowerCase())
                .orElseThrow(this::invalidCredentials);
        if (!user.getEmail().equals(ticket.getEmail()) || user.getPasswordHash() == null ||
                !passwordEncoder.matches(password, user.getPasswordHash())) {
            throw invalidCredentials();
        }
        identities.save(new SocialIdentity(user, ticket.getProvider(), ticket.getProviderUserId()));
        ticket.attach(user);
        ticket.use();
        return user;
    }

    @Transactional
    public User register(String rawTicket, boolean termsAgreed, boolean privacyAgreed) {
        OAuthLoginTicket ticket = valid(rawTicket);
        if (!ticket.isConsentRequired()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "신규 소셜 가입 동의가 필요하지 않은 요청입니다.");
        }
        if (!termsAgreed || !privacyAgreed) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "필수 약관에 모두 동의해야 가입할 수 있습니다.");
        }
        User user = users.save(User.social(ticket.getEmail(), ticket.getName()));
        user.recordRequiredConsents(AuthController.TERMS_VERSION, AuthController.PRIVACY_VERSION);
        identities.save(new SocialIdentity(user, ticket.getProvider(), ticket.getProviderUserId()));
        ticket.attach(user);
        ticket.use();
        return user;
    }

    private OAuthLoginTicket valid(String raw) {
        OAuthLoginTicket ticket = tickets.findByTokenHash(hash(raw == null ? "" : raw))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "유효하지 않은 소셜 로그인 요청입니다."));
        if (!ticket.usable()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "소셜 로그인 요청이 만료되었거나 이미 사용되었습니다.");
        }
        return ticket;
    }

    private ResponseStatusException invalidCredentials() {
        return new ResponseStatusException(HttpStatus.UNAUTHORIZED, "기존 계정의 이메일 또는 비밀번호가 올바르지 않습니다.");
    }

    private String randomToken() {
        byte[] value = new byte[32];
        RANDOM.nextBytes(value);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private String hash(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception exception) {
            throw new IllegalStateException(exception);
        }
    }

    private String mask(String email) {
        int at = email.indexOf('@');
        if (at <= 1) return "***" + email.substring(Math.max(at, 0));
        return email.substring(0, 2) + "***" + email.substring(at);
    }

    public record TicketStatus(boolean linkingRequired, boolean consentRequired,
                               String provider, String maskedEmail) {}
}
