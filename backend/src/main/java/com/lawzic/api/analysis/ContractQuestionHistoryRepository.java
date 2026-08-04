package com.lawzic.api.analysis;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ContractQuestionHistoryRepository extends JpaRepository<ContractQuestionHistory, Long> {
    List<ContractQuestionHistory> findTop6ByContractIdAndUserEmailOrderByCreatedAtDesc(Long contractId, String email);
    List<ContractQuestionHistory> findAllByContractIdAndUserEmailOrderByCreatedAtAsc(Long contractId, String email);
    void deleteAllByContractId(Long contractId);
    void deleteAllByUserEmail(String email);
}
