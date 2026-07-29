package com.lawzic.api.auth;

import com.lawzic.api.analysis.AnalysisService;
import com.lawzic.api.analysis.LegalConsultationHistoryRepository;
import com.lawzic.api.contract.Contract;
import com.lawzic.api.contract.ContractService;
import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
@RequiredArgsConstructor
public class AccountService {
    private final UserRepository users;
    private final PasswordEncoder passwordEncoder;
    private final ContractService contractService;
    private final AnalysisService analysisService;
    private final LegalConsultationHistoryRepository consultationHistory;

    @Transactional
    public User updateAccount(String email, String name, String currentPassword, String newPassword) {
        User user = users.findByEmail(email)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
        if (currentPassword == null || !passwordEncoder.matches(currentPassword, user.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "현재 비밀번호가 올바르지 않습니다.");
        }
        String normalizedName = name == null ? "" : name.trim();
        if (normalizedName.isBlank() || normalizedName.length() > 50) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "이름은 1자 이상 50자 이하로 입력하세요.");
        }
        user.updateName(normalizedName);
        if (newPassword != null && !newPassword.isBlank()) {
            if (newPassword.length() < 8 || newPassword.length() > 72) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "새 비밀번호는 8자 이상 72자 이하로 입력하세요.");
            }
            user.updatePassword(passwordEncoder.encode(newPassword));
        }
        return user;
    }

    public void deleteAccount(String email, String password) {
        if (password == null || password.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "비밀번호를 입력하세요.");
        }
        User user = users.findByEmail(email)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
        if (!passwordEncoder.matches(password, user.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "비밀번호가 올바르지 않습니다.");
        }

        List<Contract> ownedContracts = List.copyOf(contractService.list(email));
        for (Contract contract : ownedContracts) {
            if (contract.getStatus() == Contract.Status.PROCESSING) {
                analysisService.cancel(contract.getId(), email);
            }
            contractService.delete(contract.getId(), email);
        }
        contractService.deleteUserUploadDirectory(user.getId());
        consultationHistory.deleteAllByUserEmail(email);
        consultationHistory.flush();
        users.delete(user);
        users.flush();
    }
}
