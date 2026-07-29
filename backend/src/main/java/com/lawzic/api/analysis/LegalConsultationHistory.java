package com.lawzic.api.analysis;

import com.lawzic.api.user.User;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Getter
@Entity
@Table(name = "legal_consultation_history")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class LegalConsultationHistory {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    private User user;
    @Column(nullable = false, length = 500)
    private String question;
    @Lob @Column(nullable = false)
    private String responseJson;
    @Column(nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    public LegalConsultationHistory(User user, String question, String responseJson) {
        this.user = user;
        this.question = question;
        this.responseJson = responseJson;
    }
}
