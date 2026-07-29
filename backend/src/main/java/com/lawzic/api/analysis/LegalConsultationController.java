package com.lawzic.api.analysis;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.security.Principal;

@RestController
@RequestMapping("/api/legal-consultation")
@RequiredArgsConstructor
public class LegalConsultationController {
    private static final int MAX_HISTORY = 12;
    private final LegalConsultationService consultationService;

    public record ChatMessage(String role, String content) {}
    public record ChatRequest(String question, List<ChatMessage> history) {}

    @PostMapping("/messages")
    public JsonNode chat(@RequestBody ChatRequest request, Principal principal) {
        if (request == null || request.question() == null
                || request.question().trim().length() < 2
                || request.question().length() > 500) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST, "질문은 2자 이상 500자 이하로 입력하세요."
            );
        }
        List<ChatMessage> requestedHistory = request.history() == null ? List.of() : request.history();
        if (requestedHistory.size() > MAX_HISTORY) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST, "대화 기록은 최근 12개까지만 전송할 수 있습니다."
            );
        }
        List<Map<String, String>> history = requestedHistory.stream()
                .filter(item -> item != null
                        && ("user".equals(item.role()) || "assistant".equals(item.role()))
                        && item.content() != null
                        && !item.content().isBlank()
                        && item.content().length() <= 2000)
                .map(item -> Map.of("role", item.role(), "content", item.content().trim()))
                .toList();
        return consultationService.chat(principal.getName(), request.question().trim(), history);
    }

    @GetMapping("/history")
    public List<LegalConsultationService.HistoryResponse> history(Principal principal) {
        return consultationService.history(principal.getName());
    }

    @DeleteMapping("/history")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void clearHistory(Principal principal) {
        consultationService.clearHistory(principal.getName());
    }
}
