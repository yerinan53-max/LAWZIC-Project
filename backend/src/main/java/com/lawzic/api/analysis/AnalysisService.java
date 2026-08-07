package com.lawzic.api.analysis;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lawzic.api.contract.Contract;
import com.lawzic.api.contract.ContractRepository;
import com.lawzic.api.contract.ContractService;
import com.lawzic.api.contract.PdfTextLayerService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import jakarta.annotation.PreDestroy;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicLong;

@Service
@RequiredArgsConstructor
@Slf4j
public class AnalysisService {
    private final ContractService contractService;
    private final ContractRepository contracts;
    private final AnalysisResultRepository results;
    private final AiClient aiClient;
    private final ObjectMapper objectMapper;
    private final ContractQuestionHistoryRepository questionHistory;
    private final PdfTextLayerService pdfTextLayerService;
    private final ExecutorService executor = Executors.newCachedThreadPool();
    private final ConcurrentHashMap<Long, Future<?>> jobs = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<Long, Long> activeRuns = new ConcurrentHashMap<>();
    private final AtomicLong runSequence = new AtomicLong();

    @Transactional
    public synchronized Contract start(Long contractId, String email) {
        Contract contract = contractService.owned(contractId, email);
        pdfTextLayerService.requireExtractableText(contract.getFilePath());
        Future<?> current = jobs.get(contractId);
        if (current != null && !current.isDone()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 분석 중인 계약서입니다.");
        }
        long runId = runSequence.incrementAndGet();
        activeRuns.put(contractId, runId);
        contract.markProcessing();
        contracts.save(contract);
        Future<?> job = executor.submit(() -> performAnalysis(contractId, contract.getFilePath(), runId));
        jobs.put(contractId, job);
        return contract;
    }

    private void performAnalysis(Long contractId, String filePath, long runId) {
        try {
            JsonNode result = aiClient.analyze(contractId, filePath);
            String json = objectMapper.writeValueAsString(result);
            synchronized (this) {
                if (!isActiveRun(contractId, runId) || Thread.currentThread().isInterrupted()) return;
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
                if (!isActiveRun(contractId, runId) || Thread.currentThread().isInterrupted()) return;
                contracts.findById(contractId).ifPresent(contract -> {
                    contract.markFailed();
                    contracts.save(contract);
                });
            }
        } finally {
            // 이전 실행의 finally가 같은 계약서의 새 재분석 작업을 제거하지 못하게 한다.
            if (activeRuns.remove(contractId, runId)) {
                jobs.remove(contractId);
            }
        }
    }

    private boolean isActiveRun(Long contractId, long runId) {
        return Long.valueOf(runId).equals(activeRuns.get(contractId));
    }

    @Transactional
    public synchronized Contract cancel(Long contractId, String email) {
        Contract contract = contractService.owned(contractId, email);
        if (contract.getStatus() != Contract.Status.PROCESSING) {
            // 완료/실패/이미 취소된 직후에 중복 요청이 도착해도 취소 API는 안전하게 응답한다.
            return contract;
        }
        // 실행 번호를 먼저 무효화해, interrupt를 무시하고 늦게 반환한 HTTP 호출도 결과를 저장하지 못하게 한다.
        activeRuns.remove(contractId);
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

    @Transactional
    public JsonNode question(Long contractId, String email, String question) {
        if (question == null || question.trim().length() < 2 || question.length() > 500) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "질문은 2자 이상 500자 이하로 입력하세요.");
        }
        Contract contract = contractService.owned(contractId, email);
        var recent = questionHistory.findTop6ByContractIdAndUserEmailOrderByCreatedAtDesc(contractId, email);
        var history = new java.util.ArrayList<java.util.Map<String, String>>();
        for (int index = recent.size() - 1; index >= 0; index--) {
            ContractQuestionHistory item = recent.get(index);
            history.add(java.util.Map.of("role", "user", "content", item.getQuestion()));
            try {
                history.add(java.util.Map.of(
                        "role", "assistant",
                        "content", objectMapper.readTree(item.getResponseJson()).path("answer").asText("")
                ));
            } catch (JsonProcessingException ignored) {
                // 손상된 과거 응답 하나 때문에 현재 질문을 실패시키지 않는다.
            }
        }
        JsonNode response;
        try {
            response = aiClient.question(
                    contractId, question.trim(), objectMapper.writeValueAsString(history), contract.getFilePath()
            );
            questionHistory.save(new ContractQuestionHistory(
                    contract, contract.getUser(), question.trim(), objectMapper.writeValueAsString(response)
            ));
        } catch (JsonProcessingException ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "질문 이력을 처리할 수 없습니다.");
        }
        return response;
    }

    @Transactional(readOnly = true)
    public java.util.List<QuestionHistoryResponse> questionHistory(Long contractId, String email) {
        contractService.owned(contractId, email);
        return questionHistory.findAllByContractIdAndUserEmailOrderByCreatedAtAsc(contractId, email).stream()
                .map(item -> {
                    try {
                        return new QuestionHistoryResponse(
                                item.getId(), item.getQuestion(), objectMapper.readTree(item.getResponseJson()), item.getCreatedAt()
                        );
                    } catch (JsonProcessingException ex) {
                        throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "저장된 질문 이력을 읽을 수 없습니다.");
                    }
                }).toList();
    }

    public record QuestionHistoryResponse(Long id, String question, JsonNode response, java.time.Instant createdAt) {}

    @Transactional(readOnly = true)
    public byte[] report(Long contractId, String email) {
        Contract contract = contractService.owned(contractId, email);
        String json = results.findByContractId(contractId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "아직 분석 결과가 없습니다."))
                .getResultJson();
        return aiClient.report(contract.getOriginalFilename(), json);
    }
}
