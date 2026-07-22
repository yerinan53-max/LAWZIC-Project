package com.lawzic.api.contract;

import java.time.Instant;

public final class ContractDtos {
    private ContractDtos() {}
    public record ContractResponse(Long id, String filename, long fileSize, String status, Instant uploadedAt) {
        public static ContractResponse from(Contract c) {
            return new ContractResponse(c.getId(), c.getOriginalFilename(), c.getFileSize(), c.getStatus().name(), c.getUploadedAt());
        }
    }
}
