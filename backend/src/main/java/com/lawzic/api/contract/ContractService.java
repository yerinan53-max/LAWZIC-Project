package com.lawzic.api.contract;

import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ContractService {
    private final ContractRepository contracts;
    private final UserRepository users;
    @Value("${app.upload-dir}") private String uploadDir;

    public Contract upload(String email, MultipartFile file) {
        validatePdf(file);
        User user = users.findByEmail(email).orElseThrow();
        String storedName = UUID.randomUUID() + ".pdf";
        try {
            Path userDir = Path.of(uploadDir, user.getId().toString()).toAbsolutePath().normalize();
            Files.createDirectories(userDir);
            Path destination = userDir.resolve(storedName).normalize();
            if (!destination.startsWith(userDir)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "잘못된 파일 경로입니다.");
            file.transferTo(destination);
            return contracts.save(new Contract(user, safeName(file.getOriginalFilename()), storedName,
                    destination.toString(), file.getSize()));
        } catch (IOException ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "파일 저장에 실패했습니다.");
        }
    }

    public List<Contract> list(String email) { return contracts.findAllByUserEmailOrderByUploadedAtDesc(email); }

    public Contract owned(Long id, String email) {
        return contracts.findByIdAndUserEmail(id, email)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "계약서를 찾을 수 없습니다."));
    }

    private void validatePdf(MultipartFile file) {
        if (file.isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "PDF 파일을 선택하세요.");
        String name = file.getOriginalFilename();
        if (name == null || !name.toLowerCase().endsWith(".pdf"))
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "PDF 파일만 업로드할 수 있습니다.");
        try {
            byte[] header = file.getInputStream().readNBytes(4);
            if (header.length < 4 || header[0] != '%' || header[1] != 'P' || header[2] != 'D' || header[3] != 'F')
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "올바른 PDF 파일이 아닙니다.");
        } catch (IOException ex) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "파일을 읽을 수 없습니다.");
        }
    }

    private String safeName(String name) { return Path.of(name == null ? "contract.pdf" : name).getFileName().toString(); }
}
