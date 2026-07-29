package com.lawzic.api.auth;

import com.lawzic.api.user.User;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Getter
@Entity
@Table(name = "social_identities",
        uniqueConstraints = @UniqueConstraint(name = "uk_social_provider_subject", columnNames = {"provider", "providerUserId"}))
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SocialIdentity {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    private User user;
    @Column(nullable = false, length = 20)
    private String provider;
    @Column(nullable = false, length = 255)
    private String providerUserId;
    @Column(nullable = false, updatable = false)
    private Instant connectedAt = Instant.now();

    public SocialIdentity(User user, String provider, String providerUserId) {
        this.user = user;
        this.provider = provider;
        this.providerUserId = providerUserId;
    }
}
