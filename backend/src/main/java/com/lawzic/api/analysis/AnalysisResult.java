package com.lawzic.api.analysis;

import com.lawzic.api.contract.Contract;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Getter
@Entity
@Table(name = "analysis_results")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class AnalysisResult {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @OneToOne(fetch = FetchType.LAZY, optional = false)
    private Contract contract;
    @Lob
    @Column(nullable = false, columnDefinition = "LONGTEXT")
    private String resultJson;
    @Column(nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    public AnalysisResult(Contract contract, String resultJson) {
        this.contract = contract;
        this.resultJson = resultJson;
    }

    public void replace(String resultJson) { this.resultJson = resultJson; }
}
