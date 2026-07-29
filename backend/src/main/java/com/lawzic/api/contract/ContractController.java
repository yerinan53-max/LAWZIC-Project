package com.lawzic.api.contract;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ContentDisposition;
import java.nio.charset.StandardCharsets;

import java.security.Principal;
import java.util.List;

import static com.lawzic.api.contract.ContractDtos.ContractResponse;

@RestController
@RequestMapping("/api/contracts")
@RequiredArgsConstructor
public class ContractController {
    private final ContractService service;
    private final PdfRenderService pdfRenderService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ContractResponse upload(@RequestPart("file") MultipartFile file, Principal principal) {
        return ContractResponse.from(service.upload(principal.getName(), file));
    }

    @GetMapping
    public List<ContractResponse> list(Principal principal) {
        return service.list(principal.getName()).stream().map(ContractResponse::from).toList();
    }

    @GetMapping("/{id}")
    public ContractResponse get(@PathVariable Long id, Principal principal) {
        return ContractResponse.from(service.owned(id, principal.getName()));
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id, Principal principal) {
        service.delete(id, principal.getName());
    }

    @GetMapping("/{id}/file")
    public ResponseEntity<FileSystemResource> file(@PathVariable Long id, Principal principal) {
        Contract contract = service.owned(id, principal.getName());
        FileSystemResource resource = new FileSystemResource(contract.getFilePath());
        ContentDisposition disposition = ContentDisposition.inline()
                .filename(contract.getOriginalFilename(), StandardCharsets.UTF_8).build();
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .contentLength(contract.getFileSize())
                .header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
                .body(resource);
    }

    @GetMapping(value = "/{id}/pages/{page}", produces = MediaType.IMAGE_PNG_VALUE)
    public byte[] page(@PathVariable Long id, @PathVariable int page, Principal principal) {
        return pdfRenderService.render(id, principal.getName(), page);
    }
}
