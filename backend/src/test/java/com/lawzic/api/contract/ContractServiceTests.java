package com.lawzic.api.contract;

import com.lawzic.api.analysis.AnalysisResultRepository;
import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ContractServiceTests {
    @Mock ContractRepository contracts;
    @Mock AnalysisResultRepository analysisResults;
    @Mock UserRepository users;
    @TempDir Path uploadDir;

    @Test
    void deleteRemovesOnlyTheRequestedContractAndItsFile() throws Exception {
        Path firstFile = Files.writeString(uploadDir.resolve("first.pdf"), "%PDF first");
        Path secondFile = Files.writeString(uploadDir.resolve("second.pdf"), "%PDF second");
        Contract first = new Contract(mock(User.class), "first.pdf", "first.pdf", firstFile.toString(), Files.size(firstFile));
        Contract second = new Contract(mock(User.class), "second.pdf", "second.pdf", secondFile.toString(), Files.size(secondFile));

        ContractService service = new ContractService(contracts, analysisResults, users);
        ReflectionTestUtils.setField(service, "uploadDir", uploadDir.toString());
        when(contracts.findByIdAndUserEmail(1L, "owner@example.com")).thenReturn(Optional.of(first));
        when(analysisResults.findByContractId(1L)).thenReturn(Optional.empty());

        service.delete(1L, "owner@example.com");

        verify(analysisResults).findByContractId(1L);
        verify(contracts).delete(first);
        verify(contracts, never()).delete(second);
        assertFalse(Files.exists(firstFile));
        assertTrue(Files.exists(secondFile));
    }
}
