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
import java.util.List;
import java.util.Map;

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

    public JsonNode question(String question, String filePath) {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("question", question);
        body.add("file", new FileSystemResource(Path.of(filePath)));
        return builder.baseUrl(aiBaseUrl).build().post().uri("/internal/v1/question")
                .contentType(MediaType.MULTIPART_FORM_DATA).body(body).retrieve().body(JsonNode.class);
    }

    public JsonNode legalChat(String question, List<Map<String, String>> history) {
        Map<String, Object> body = Map.of("question", question, "history", history);
        return builder.baseUrl(aiBaseUrl).build().post().uri("/internal/v1/legal-chat")
                .contentType(MediaType.APPLICATION_JSON).body(body).retrieve().body(JsonNode.class);
    }

    public byte[] report(String filename, String analysisJson) {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("filename", filename);
        body.add("analysis_json", analysisJson);
        return builder.baseUrl(aiBaseUrl).build().post().uri("/internal/v1/report")
                .contentType(MediaType.MULTIPART_FORM_DATA).body(body).retrieve().body(byte[].class);
    }
}
