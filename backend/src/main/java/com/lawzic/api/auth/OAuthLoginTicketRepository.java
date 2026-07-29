package com.lawzic.api.auth;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface OAuthLoginTicketRepository extends JpaRepository<OAuthLoginTicket, Long> {
    Optional<OAuthLoginTicket> findByTokenHash(String tokenHash);
    void deleteAllByUserEmail(String email);
}
