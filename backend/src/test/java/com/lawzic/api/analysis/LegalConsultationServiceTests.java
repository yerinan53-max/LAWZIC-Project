package com.lawzic.api.analysis;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class LegalConsultationServiceTests {
    @Mock AiClient aiClient;
    @Mock UserRepository users;
    @Mock LegalConsultationHistoryRepository historyRepository;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void savesQuestionAndAiResponseForMyPageHistory() throws Exception {
        User user = new User("owner@example.com", "encoded", "사용자");
        var aiResponse = objectMapper.readTree("""
                {"answer":"연장근로 답변","legal_references":[],"insufficient_evidence":false}
                """);
        when(users.findByEmail("owner@example.com")).thenReturn(Optional.of(user));
        when(aiClient.legalChat("연장근로 한도는?", List.of())).thenReturn(aiResponse);
        LegalConsultationService service = new LegalConsultationService(
                aiClient, users, historyRepository, objectMapper
        );

        service.chat("owner@example.com", "연장근로 한도는?", List.of());

        ArgumentCaptor<LegalConsultationHistory> captor =
                ArgumentCaptor.forClass(LegalConsultationHistory.class);
        verify(historyRepository).save(captor.capture());
        assertEquals("연장근로 한도는?", captor.getValue().getQuestion());
        assertEquals("연장근로 답변", objectMapper.readTree(captor.getValue().getResponseJson()).path("answer").asText());
    }

    @Test
    void clearsOnlyCurrentUsersConsultationHistory() {
        LegalConsultationService service = new LegalConsultationService(
                aiClient, users, historyRepository, objectMapper
        );

        service.clearHistory("owner@example.com");

        verify(historyRepository).deleteAllByUserEmail("owner@example.com");
        verify(historyRepository).flush();
    }
}
