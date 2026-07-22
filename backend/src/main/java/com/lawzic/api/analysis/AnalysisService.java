package com.lawzic.api.analysis;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lawzic.api.contract.Contract;
import com.lawzic.api.contract.ContractRepository;
import com.lawzic.api.contract.ContractService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
@RequiredArgsConstructor
public class AnalysisService {
    private final ContractService contractService;
    private final ContractRepository contracts;
    private final AnalysisResultRepository results;
    private final AiClient aiClient;
    private final ObjectMapper objectMapper;

    @Transactional
    public JsonNode analyze(Long contractId, String email) {
        Contract contract = contractService.owned(contractId, email);
        contract.markProcessing();
        contracts.save(contract);
        try {
            JsonNode result = aiClient.analyze(contractId, contract.getFilePath());
            String json = objectMapper.writeValueAsString(result);
            AnalysisResult entity = results.findByContractId(contractId).orElseGet(() -> new AnalysisResult(contract, json));
            entity.replace(json);
            results.save(entity);
            contract.markCompleted();
            return result;
        } catch (Exception ex) {
            contract.markFailed();
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "AI 분석 서버 호출에 실패했습니다.");
        }
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
}
