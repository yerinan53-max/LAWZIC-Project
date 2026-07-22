package com.lawzic.api.contract;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.security.Principal;
import java.util.List;

import static com.lawzic.api.contract.ContractDtos.ContractResponse;

@RestController
@RequestMapping("/api/contracts")
@RequiredArgsConstructor
public class ContractController {
    private final ContractService service;

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
}
