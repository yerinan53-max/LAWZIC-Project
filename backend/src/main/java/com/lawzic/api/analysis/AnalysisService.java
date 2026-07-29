package com.lawzic.api.analysis;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lawzic.api.contract.Contract;
import com.lawzic.api.contract.ContractRepository;
import com.lawzic.api.contract.ContractService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import jakarta.annotation.PreDestroy;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

@Service
@RequiredArgsConstructor
@Slf4j
public class AnalysisService {
    private final ContractService contractService;
    private final ContractRepository contracts;
    private final AnalysisResultRepository results;
    private final AiClient aiClient;
    private final ObjectMapper objectMapper;
    private final ExecutorService executor = Executors.newCachedThreadPool();
    private final ConcurrentHashMap<Long, Future<?>> jobs = new ConcurrentHashMap<>();
    private final Set<Long> cancelled = ConcurrentHashMap.newKeySet();

    @Transactional
    public synchronized Contract start(Long contractId, String email) {
        Contract contract = contractService.owned(contractId, email);
        Future<?> current = jobs.get(contractId);
        if (current != null && !current.isDone()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 분석 중인 계약서입니다.");
        }
        cancelled.remove(contractId);
        contract.markProcessing();
        contracts.save(contract);
        Future<?> job = executor.submit(() -> performAnalysis(contractId, contract.getFilePath()));
        jobs.put(contractId, job);
        return contract;
    }

    private void performAnalysis(Long contractId, String filePath) {
        try {
            JsonNode result = aiClient.analyze(contractId, filePath);
            String json = objectMapper.writeValueAsString(result);
            synchronized (this) {
                if (cancelled.contains(contractId) || Thread.currentThread().isInterrupted()) return;
                Contract contract = contracts.findById(contractId).orElseThrow();
                AnalysisResult entity = results.findByContractId(contractId)
                        .orElseGet(() -> new AnalysisResult(contract, json));
                entity.replace(json);
                results.save(entity);
                contract.markCompleted();
                contracts.save(contract);
            }
        } catch (Exception ex) {
            log.error("계약서 AI 분석 처리 실패: contractId={}", contractId, ex);
            synchronized (this) {
                if (cancelled.contains(contractId) || Thread.currentThread().isInterrupted()) return;
                contracts.findById(contractId).ifPresent(contract -> {
                    contract.markFailed();
                    contracts.save(contract);
                });
            }
        } finally {
            jobs.remove(contractId);
            cancelled.remove(contractId);
        }
    }

    @Transactional
    public synchronized Contract cancel(Long contractId, String email) {
        Contract contract = contractService.owned(contractId, email);
        if (contract.getStatus() != Contract.Status.PROCESSING) {
            // 완료/실패/이미 취소된 직후에 중복 요청이 도착해도 취소 API는 안전하게 응답한다.
            return contract;
        }
        cancelled.add(contractId);
        Future<?> job = jobs.remove(contractId);
        if (job != null) job.cancel(true);
        contract.markCancelled();
        contracts.save(contract);
        return contract;
    }

    @PreDestroy
    void shutdown() {
        executor.shutdownNow();
    }

    @Transactional(readOnly = true)
    public JsonNode result(Long contractId, String email) {
        contractService.owned(contractId, email);
        String json = results.findByContractId(contractId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "아직 분석 결과가 없습니다."))
                .getResultJson();
        try { return objectMapper.readTree(json); }
        catch (JsonProcessingException ex) { throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "저장된 결과를 읽을 수 없습니다."); }
    }

    @Transactional(readOnly = true)
    public JsonNode question(Long contractId, String email, String question) {
        if (question == null || question.trim().length() < 2 || question.length() > 500) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "질문은 2자 이상 500자 이하로 입력하세요.");
        }
        Contract contract = contractService.owned(contractId, email);
        return aiClient.question(question.trim(), contract.getFilePath());
    }

    @Transactional(readOnly = true)
    public byte[] report(Long contractId, String email) {
        Contract contract = contractService.owned(contractId, email);
        String json = results.findByContractId(contractId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "아직 분석 결과가 없습니다."))
                .getResultJson();
        return aiClient.report(contract.getOriginalFilename(), json);
    }
}
