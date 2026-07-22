package com.lawzic.api.analysis;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;

import java.nio.file.Path;

@Component
@RequiredArgsConstructor
public class AiClient {
    private final RestClient.Builder builder;
    @Value("${app.ai-base-url}") private String aiBaseUrl;

    public JsonNode analyze(Long contractId, String filePath) {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("contract_id", contractId.toString());
        body.add("file", new FileSystemResource(Path.of(filePath)));
        return builder.baseUrl(aiBaseUrl).build().post().uri("/internal/v1/analyze")
                .contentType(MediaType.MULTIPART_FORM_DATA).body(body).retrieve().body(JsonNode.class);
    }
}
