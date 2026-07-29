package com.lawzic.api.analysis;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface LegalConsultationHistoryRepository extends JpaRepository<LegalConsultationHistory, Long> {
    List<LegalConsultationHistory> findAllByUserEmailOrderByCreatedAtDesc(String email);
    void deleteAllByUserEmail(String email);
}
