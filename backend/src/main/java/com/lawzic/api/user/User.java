package com.lawzic.api.user;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Getter
@Entity
@Table(name = "users")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(nullable = false, unique = true, length = 150)
    private String email;
    @Column
    private String passwordHash;
    @Column(nullable = false, length = 50)
    private String name;
    @Column(nullable = false, length = 20)
    private String role = "ROLE_USER";
    @Column(nullable = false, updatable = false)
    private Instant createdAt = Instant.now();
    private Instant termsAgreedAt;
    private Instant privacyAgreedAt;
    @Column(length = 20)
    private String termsVersion;
    @Column(length = 20)
    private String privacyVersion;

    public User(String email, String passwordHash, String name) {
        this.email = email.toLowerCase();
        this.passwordHash = passwordHash;
        this.name = name;
    }

    public void updateName(String name) { this.name = name; }
    public void updatePassword(String passwordHash) { this.passwordHash = passwordHash; }
    public void recordRequiredConsents(String termsVersion, String privacyVersion) {
        Instant now = Instant.now();
        this.termsAgreedAt = now;
        this.privacyAgreedAt = now;
        this.termsVersion = termsVersion;
        this.privacyVersion = privacyVersion;
    }

    public static User social(String email, String name) {
        return new User(email, null, name);
    }
}
