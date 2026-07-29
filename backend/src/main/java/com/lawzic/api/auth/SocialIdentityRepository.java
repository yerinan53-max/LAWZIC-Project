package com.lawzic.api.auth;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface SocialIdentityRepository extends JpaRepository<SocialIdentity, Long> {
    Optional<SocialIdentity> findByProviderAndProviderUserId(String provider, String providerUserId);
    void deleteAllByUserEmail(String email);
}
