package com.lawzic.api.analysis;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lawzic.api.contract.Contract;
import com.lawzic.api.contract.ContractRepository;
import com.lawzic.api.contract.ContractService;
import com.lawzic.api.contract.PdfTextLayerService;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.Optional;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

class AnalysisServiceTests {
    private final ContractService contractService = mock(ContractService.class);
    private final ContractRepository contracts = mock(ContractRepository.class);
    private final AnalysisResultRepository results = mock(AnalysisResultRepository.class);
    private final AiClient aiClient = mock(AiClient.class);
    private final ContractQuestionHistoryRepository questionHistory = mock(ContractQuestionHistoryRepository.class);
    private final PdfTextLayerService pdfTextLayerService = mock(PdfTextLayerService.class);
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final AnalysisService service = new AnalysisService(
            contractService, contracts, results, aiClient, objectMapper, questionHistory, pdfTextLayerService
    );

    @AfterEach
    void tearDown() {
        service.shutdown();
    }

    @Test
    void scannedPdfIsRejectedBeforeAnalysisJobStarts() {
        Contract contract = mock(Contract.class);
        when(contract.getFilePath()).thenReturn("scanned.pdf");
        when(contractService.owned(1L, "owner@example.com")).thenReturn(contract);
        doThrow(new org.springframework.web.server.ResponseStatusException(
                org.springframework.http.HttpStatus.UNPROCESSABLE_ENTITY,
                "이 PDF는 스캔 이미지로 구성되어 텍스트를 인식할 수 없습니다."
        )).when(pdfTextLayerService).requireExtractableText("scanned.pdf");

        var error = assertThrows(
                org.springframework.web.server.ResponseStatusException.class,
                () -> service.start(1L, "owner@example.com")
        );

        assertEquals(422, error.getStatusCode().value());
        verify(contract, never()).markProcessing();
        verify(aiClient, never()).analyze(anyLong(), anyString());
    }

    @Test
    void cancelledPreviousRunCannotOverwriteOrRemoveRestartedAnalysis() throws Exception {
        Contract contract = mock(Contract.class);
        when(contract.getFilePath()).thenReturn("contract.pdf");
        when(contract.getStatus()).thenReturn(Contract.Status.PROCESSING);
        when(contractService.owned(1L, "owner@example.com")).thenReturn(contract);
        when(contracts.findById(1L)).thenReturn(Optional.of(contract));
        when(results.findByContractId(1L)).thenReturn(Optional.empty());

        CountDownLatch firstStarted = new CountDownLatch(1);
        CountDownLatch releaseFirst = new CountDownLatch(1);
        CountDownLatch firstReturned = new CountDownLatch(1);
        CountDownLatch secondStarted = new CountDownLatch(1);
        CountDownLatch releaseSecond = new CountDownLatch(1);
        AtomicInteger calls = new AtomicInteger();
        ObjectNode response = objectMapper.createObjectNode().put("summary", "ok");

        when(aiClient.analyze(anyLong(), anyString())).thenAnswer(invocation -> {
            if (calls.getAndIncrement() == 0) {
                firstStarted.countDown();
                // 실제 HTTP 클라이언트처럼 interrupt만으로 즉시 끝나지 않는 이전 요청을 재현한다.
                while (true) {
                    try {
                        if (releaseFirst.await(20, TimeUnit.MILLISECONDS)) break;
                    } catch (InterruptedException ignored) {
                        // 취소 신호를 받았지만 네트워크 호출이 즉시 끝나지 않는 상황을 의도적으로 재현한다.
                    }
                }
                firstReturned.countDown();
                return response;
            }
            secondStarted.countDown();
            releaseSecond.await(2, TimeUnit.SECONDS);
            return response;
        });

        service.start(1L, "owner@example.com");
        assertTrue(firstStarted.await(1, TimeUnit.SECONDS));
        service.cancel(1L, "owner@example.com");
        service.start(1L, "owner@example.com");
        assertTrue(secondStarted.await(1, TimeUnit.SECONDS));

        releaseFirst.countDown();
        assertTrue(firstReturned.await(1, TimeUnit.SECONDS));
        Thread.sleep(100);
        verify(results, never()).save(any());
        verify(contract, never()).markCompleted();

        releaseSecond.countDown();
        verify(results, timeout(1500).times(1)).save(any());
        verify(contract, timeout(1500).times(1)).markCompleted();
    }
}
