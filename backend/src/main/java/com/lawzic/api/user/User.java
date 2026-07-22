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
    @Column(nullable = false)
    private String passwordHash;
    @Column(nullable = false, length = 50)
    private String name;
    @Column(nullable = false, length = 20)
    private String role = "ROLE_USER";
    @Column(nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    public User(String email, String passwordHash, String name) {
        this.email = email.toLowerCase();
        this.passwordHash = passwordHash;
        this.name = name;
    }
}
