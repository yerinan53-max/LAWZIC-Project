package com.lawzic.api.analysis;

import com.fasterxml.jackson.databind.JsonNode;
import com.lawzic.api.contract.ContractDtos.ContractResponse;
import com.lawzic.api.contract.ContractService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpStatus;
import java.nio.charset.StandardCharsets;

import java.security.Principal;

@RestController
@RequestMapping("/api/contracts/{contractId}/analysis")
@RequiredArgsConstructor
public class AnalysisController {
    private final AnalysisService analysisService;
    private final ContractService contractService;

    @PostMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    public ContractResponse analyze(@PathVariable Long contractId, Principal principal) {
        return ContractResponse.from(analysisService.start(contractId, principal.getName()));
    }

    @PostMapping("/cancel")
    public ContractResponse cancel(@PathVariable Long contractId, Principal principal) {
        return ContractResponse.from(analysisService.cancel(contractId, principal.getName()));
    }

    @GetMapping
    public JsonNode result(@PathVariable Long contractId, Principal principal) {
        return analysisService.result(contractId, principal.getName());
    }

    @GetMapping("/status")
    public ContractResponse status(@PathVariable Long contractId, Principal principal) {
        return ContractResponse.from(contractService.owned(contractId, principal.getName()));
    }

    public record QuestionRequest(String question) {}

    @PostMapping("/questions")
    public JsonNode question(@PathVariable Long contractId, @RequestBody QuestionRequest request, Principal principal) {
        return analysisService.question(contractId, principal.getName(), request.question());
    }

    @GetMapping("/questions")
    public java.util.List<AnalysisService.QuestionHistoryResponse> questionHistory(
            @PathVariable Long contractId, Principal principal) {
        return analysisService.questionHistory(contractId, principal.getName());
    }

    @GetMapping("/report")
    public ResponseEntity<byte[]> report(@PathVariable Long contractId, Principal principal) {
        byte[] content = analysisService.report(contractId, principal.getName());
        ContentDisposition disposition = ContentDisposition.attachment()
                .filename("LAWZIC-analysis-report.pdf", StandardCharsets.UTF_8).build();
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
                .body(content);
    }
}
