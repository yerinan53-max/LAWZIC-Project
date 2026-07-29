package com.lawzic.api.contract;

import com.lawzic.api.analysis.AnalysisResultRepository;
import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
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
    private final AnalysisResultRepository analysisResults;
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

    @Transactional
    public void delete(Long id, String email) {
        Contract contract = owned(id, email);
        if (contract.getStatus() == Contract.Status.PROCESSING) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "분석 중인 계약서는 삭제할 수 없습니다.");
        }

        Path uploadRoot = Path.of(uploadDir).toAbsolutePath().normalize();
        Path storedFile = Path.of(contract.getFilePath()).toAbsolutePath().normalize();
        if (!storedFile.startsWith(uploadRoot)) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "저장 파일 경로가 안전하지 않습니다.");
        }

        try {
            Files.deleteIfExists(storedFile);
        } catch (IOException ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "계약서 파일 삭제에 실패했습니다.");
        }

        analysisResults.findByContractId(id).ifPresent(analysisResults::delete);
        analysisResults.flush();
        contracts.delete(contract);
    }

    private void validatePdf(MultipartFile file) {
        if (file.isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "PDF 파일을 선택하세요.");
        if (file.getSize() > 10L * 1024 * 1024)
            throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, "10MB 이하의 PDF 파일만 업로드할 수 있습니다.");
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
