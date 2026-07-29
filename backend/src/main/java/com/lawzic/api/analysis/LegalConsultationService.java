package com.lawzic.api.analysis;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class LegalConsultationService {
    private final AiClient aiClient;
    private final UserRepository users;
    private final LegalConsultationHistoryRepository historyRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public JsonNode chat(String email, String question, List<Map<String, String>> history) {
        User user = users.findByEmail(email)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
        JsonNode response = aiClient.legalChat(question, history);
        historyRepository.save(new LegalConsultationHistory(user, question, response.toString()));
        return response;
    }

    @Transactional(readOnly = true)
    public List<HistoryResponse> history(String email) {
        return historyRepository.findAllByUserEmailOrderByCreatedAtDesc(email).stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional
    public void clearHistory(String email) {
        historyRepository.deleteAllByUserEmail(email);
        historyRepository.flush();
    }

    private HistoryResponse toResponse(LegalConsultationHistory entity) {
        try {
            JsonNode response = objectMapper.readTree(entity.getResponseJson());
            return new HistoryResponse(
                    entity.getId(),
                    entity.getQuestion(),
                    response.path("answer").asText(""),
                    response.path("legal_references"),
                    response.path("insufficient_evidence").asBoolean(false),
                    entity.getCreatedAt()
            );
        } catch (JsonProcessingException ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "저장된 상담 이력을 읽을 수 없습니다.");
        }
    }

    public record HistoryResponse(
            Long id,
            String question,
            String answer,
            JsonNode legalReferences,
            boolean insufficientEvidence,
            Instant createdAt
    ) {}
}
