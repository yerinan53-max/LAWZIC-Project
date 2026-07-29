package com.lawzic.api.auth;

import com.lawzic.api.user.User;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Getter
@Entity
@Table(name = "oauth_login_tickets", indexes = @Index(name = "idx_oauth_ticket_hash", columnList = "tokenHash", unique = true))
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class OAuthLoginTicket {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(nullable = false, unique = true, length = 64)
    private String tokenHash;
    @Column(nullable = false, length = 20)
    private String provider;
    @Column(nullable = false, length = 255)
    private String providerUserId;
    @Column(nullable = false, length = 150)
    private String email;
    @Column(nullable = false, length = 50)
    private String name;
    @ManyToOne(fetch = FetchType.LAZY)
    private User user;
    @Column(nullable = false)
    private boolean linkingRequired;
    @Column(nullable = false)
    private boolean consentRequired;
    @Column(nullable = false)
    private Instant expiresAt;
    private Instant usedAt;

    public OAuthLoginTicket(String tokenHash, String provider, String providerUserId,
                            String email, String name, User user, boolean linkingRequired,
                            boolean consentRequired, Instant expiresAt) {
        this.tokenHash = tokenHash;
        this.provider = provider;
        this.providerUserId = providerUserId;
        this.email = email;
        this.name = name;
        this.user = user;
        this.linkingRequired = linkingRequired;
        this.consentRequired = consentRequired;
        this.expiresAt = expiresAt;
    }

    public boolean usable() { return usedAt == null && expiresAt.isAfter(Instant.now()); }
    public void attach(User user) {
        this.user = user;
        this.linkingRequired = false;
        this.consentRequired = false;
    }
    public void use() { this.usedAt = Instant.now(); }
}
