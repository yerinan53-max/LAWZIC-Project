package com.lawzic.api.analysis;

import com.fasterxml.jackson.databind.JsonNode;
import com.lawzic.api.contract.ContractDtos.ContractResponse;
import com.lawzic.api.contract.ContractService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;

@RestController
@RequestMapping("/api/contracts/{contractId}/analysis")
@RequiredArgsConstructor
public class AnalysisController {
    private final AnalysisService analysisService;
    private final ContractService contractService;

    @PostMapping
    public JsonNode analyze(@PathVariable Long contractId, Principal principal) {
        return analysisService.analyze(contractId, principal.getName());
    }

    @GetMapping
    public JsonNode result(@PathVariable Long contractId, Principal principal) {
        return analysisService.result(contractId, principal.getName());
    }

    @GetMapping("/status")
    public ContractResponse status(@PathVariable Long contractId, Principal principal) {
        return ContractResponse.from(contractService.owned(contractId, principal.getName()));
    }
}
