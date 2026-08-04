package com.lawzic.api.analysis;

import com.lawzic.api.contract.Contract;
import com.lawzic.api.user.User;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Getter
@Entity
@Table(name = "contract_question_history", indexes = {
        @Index(name = "idx_contract_question_contract_created", columnList = "contract_id,created_at")
})
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ContractQuestionHistory {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "contract_id", nullable = false)
    private Contract contract;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;
    @Column(nullable = false, length = 500)
    private String question;
    @Lob @Column(nullable = false, columnDefinition = "LONGTEXT")
    private String responseJson;
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    public ContractQuestionHistory(Contract contract, User user, String question, String responseJson) {
        this.contract = contract;
        this.user = user;
        this.question = question;
        this.responseJson = responseJson;
    }
}
