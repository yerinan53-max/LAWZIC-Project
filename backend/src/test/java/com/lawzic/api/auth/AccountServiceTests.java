package com.lawzic.api.auth;

import com.lawzic.api.analysis.AnalysisService;
import com.lawzic.api.analysis.LegalConsultationHistoryRepository;
import com.lawzic.api.contract.Contract;
import com.lawzic.api.contract.ContractService;
import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AccountServiceTests {
    @Mock UserRepository users;
    @Mock PasswordEncoder passwordEncoder;
    @Mock ContractService contractService;
    @Mock AnalysisService analysisService;
    @Mock LegalConsultationHistoryRepository consultationHistory;
    @Mock PasswordResetTokenRepository passwordResetTokens;
    @Mock SocialIdentityRepository socialIdentities;
    @Mock OAuthLoginTicketRepository oauthLoginTickets;

    @Test
    void rejectsWrongPasswordWithoutDeletingData() {
        User user = new User("owner@example.com", "encoded", "사용자");
        when(users.findByEmail("owner@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("wrong-password", "encoded")).thenReturn(false);
        AccountService service = new AccountService(
                users, passwordEncoder, contractService, analysisService, consultationHistory,
                passwordResetTokens, socialIdentities, oauthLoginTickets
        );

        assertThrows(
                ResponseStatusException.class,
                () -> service.deleteAccount("owner@example.com", "wrong-password")
        );

        verifyNoInteractions(contractService, analysisService);
        verify(users, never()).delete(any());
    }

    @Test
    void cancelsProcessingJobsAndDeletesContractsBeforeUser() {
        User user = new User("owner@example.com", "encoded", "사용자");
        Contract processing = mock(Contract.class);
        Contract completed = mock(Contract.class);
        when(processing.getId()).thenReturn(1L);
        when(processing.getStatus()).thenReturn(Contract.Status.PROCESSING);
        when(completed.getId()).thenReturn(2L);
        when(completed.getStatus()).thenReturn(Contract.Status.COMPLETED);
        when(users.findByEmail("owner@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("correct-password", "encoded")).thenReturn(true);
        when(contractService.list("owner@example.com")).thenReturn(List.of(processing, completed));
        AccountService service = new AccountService(
                users, passwordEncoder, contractService, analysisService, consultationHistory,
                passwordResetTokens, socialIdentities, oauthLoginTickets
        );

        service.deleteAccount("owner@example.com", "correct-password");

        var order = inOrder(analysisService, contractService, consultationHistory, passwordResetTokens,
                oauthLoginTickets, socialIdentities, users);
        order.verify(analysisService).cancel(1L, "owner@example.com");
        order.verify(contractService).delete(1L, "owner@example.com");
        order.verify(contractService).delete(2L, "owner@example.com");
        order.verify(contractService).deleteUserUploadDirectory(user.getId());
        order.verify(consultationHistory).deleteAllByUserEmail("owner@example.com");
        order.verify(consultationHistory).flush();
        order.verify(passwordResetTokens).deleteAllByUserEmail("owner@example.com");
        order.verify(passwordResetTokens).flush();
        order.verify(oauthLoginTickets).deleteAllByUserEmail("owner@example.com");
        order.verify(oauthLoginTickets).flush();
        order.verify(socialIdentities).deleteAllByUserEmail("owner@example.com");
        order.verify(socialIdentities).flush();
        order.verify(users).delete(user);
        order.verify(users).flush();
    }

    @Test
    void updatesNameAndPasswordAfterCurrentPasswordVerification() {
        User user = new User("owner@example.com", "encoded-old", "기존 이름");
        when(users.findByEmail("owner@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("current-password", "encoded-old")).thenReturn(true);
        when(passwordEncoder.encode("new-password")).thenReturn("encoded-new");
        AccountService service = new AccountService(
                users, passwordEncoder, contractService, analysisService, consultationHistory,
                passwordResetTokens, socialIdentities, oauthLoginTickets
        );

        User updated = service.updateAccount(
                "owner@example.com", "새 이름", "current-password", "new-password"
        );

        assertTrue(updated.getName().equals("새 이름"));
        assertTrue(updated.getPasswordHash().equals("encoded-new"));
    }
}
