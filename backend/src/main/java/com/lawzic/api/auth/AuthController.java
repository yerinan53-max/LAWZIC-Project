package com.lawzic.api.auth;

import com.lawzic.api.config.JwtService;
import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.security.Principal;

import static com.lawzic.api.auth.AuthDtos.*;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {
    static final String TERMS_VERSION = "2026-07-29";
    static final String PRIVACY_VERSION = "2026-07-29";

    private final UserRepository users;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AccountService accountService;
    private final AccountRecoveryService recoveryService;
    private final OAuthLoginService oauthLoginService;

    @PostMapping("/signup")
    @ResponseStatus(HttpStatus.CREATED)
    public UserResponse signup(@Valid @RequestBody SignupRequest request) {
        String email = request.email().trim().toLowerCase();
        if (users.existsByEmail(email)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 가입된 이메일입니다.");
        }
        User user = new User(email, passwordEncoder.encode(request.password()), request.name().trim());
        user.recordRequiredConsents(TERMS_VERSION, PRIVACY_VERSION);
        return toResponse(users.save(user));
    }

    @PostMapping("/login")
    public AuthResponse login(@Valid @RequestBody LoginRequest request) {
        User user = users.findByEmail(request.email().trim().toLowerCase())
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다."));
        if (user.getPasswordHash() == null ||
                !passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new ResponseStatusException(
                    HttpStatus.UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다.");
        }
        return new AuthResponse(jwtService.createToken(user.getEmail()), "Bearer",
                jwtService.expirationSeconds(), toResponse(user));
    }

    public record RecoveryMessage(String message) {}
    public record FindLoginIdRequest(@NotBlank @Size(max = 50) String name,
                                     @Email @NotBlank String email) {}
    public record PasswordResetRequest(@Email @NotBlank String email) {}
    public record PasswordResetConfirmRequest(@NotBlank String token,
                                              @Size(min = 8, max = 72) String newPassword) {}
    public record OAuthTicketRequest(@NotBlank String ticket) {}
    public record OAuthLinkRequest(@NotBlank String ticket, @Email @NotBlank String email,
                                   @NotBlank String password) {}
    public record OAuthRegistrationRequest(@NotBlank String ticket, boolean termsAgreed,
                                           boolean privacyAgreed) {}
    public record OAuthTicketResponse(boolean linkingRequired, boolean consentRequired,
                                      String provider, String maskedEmail) {}

    @PostMapping("/find-login-id")
    public RecoveryMessage findLoginId(@Valid @RequestBody FindLoginIdRequest request) {
        recoveryService.sendLoginId(request.name(), request.email());
        return new RecoveryMessage("입력한 정보와 일치하는 계정이 있으면 가입 이메일로 안내를 보냈습니다.");
    }

    @PostMapping("/password-reset/request")
    public RecoveryMessage requestPasswordReset(@Valid @RequestBody PasswordResetRequest request) {
        recoveryService.requestPasswordReset(request.email());
        return new RecoveryMessage("가입된 이메일이면 비밀번호 재설정 링크를 보냈습니다.");
    }

    @PostMapping("/password-reset/confirm")
    public RecoveryMessage confirmPasswordReset(@Valid @RequestBody PasswordResetConfirmRequest request) {
        recoveryService.resetPassword(request.token(), request.newPassword());
        return new RecoveryMessage("비밀번호가 변경되었습니다. 새 비밀번호로 로그인하세요.");
    }

    @PostMapping("/oauth/ticket")
    public OAuthTicketResponse inspectOAuthTicket(@Valid @RequestBody OAuthTicketRequest request) {
        var status = oauthLoginService.inspect(request.ticket());
        return new OAuthTicketResponse(status.linkingRequired(), status.consentRequired(),
                status.provider(), status.maskedEmail());
    }

    @PostMapping("/oauth/exchange")
    public AuthResponse exchangeOAuthTicket(@Valid @RequestBody OAuthTicketRequest request) {
        return authResponse(oauthLoginService.exchange(request.ticket()));
    }

    @PostMapping("/oauth/link")
    public AuthResponse linkOAuthAccount(@Valid @RequestBody OAuthLinkRequest request) {
        return authResponse(oauthLoginService.link(request.ticket(), request.email(), request.password()));
    }

    @PostMapping("/oauth/register")
    public AuthResponse registerOAuthAccount(@Valid @RequestBody OAuthRegistrationRequest request) {
        return authResponse(oauthLoginService.register(
                request.ticket(), request.termsAgreed(), request.privacyAgreed()));
    }

    @GetMapping("/me")
    public UserResponse me(Principal principal) {
        return toResponse(users.findByEmail(principal.getName()).orElseThrow());
    }

    public record UpdateAccountRequest(String name, String currentPassword, String newPassword) {}

    @PatchMapping("/me")
    public UserResponse updateAccount(@RequestBody UpdateAccountRequest request, Principal principal) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "수정할 정보를 입력하세요.");
        }
        return toResponse(accountService.updateAccount(
                principal.getName(), request.name(), request.currentPassword(), request.newPassword()));
    }

    public record DeleteAccountRequest(String password) {}

    @DeleteMapping("/me")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteAccount(@RequestBody DeleteAccountRequest request, Principal principal) {
        accountService.deleteAccount(principal.getName(), request == null ? null : request.password());
    }

    private UserResponse toResponse(User user) {
        return new UserResponse(user.getId(), user.getEmail(), user.getName());
    }

    private AuthResponse authResponse(OAuthLoginService.AuthenticatedUser user) {
        return new AuthResponse(jwtService.createToken(user.email()), "Bearer",
                jwtService.expirationSeconds(), new UserResponse(user.id(), user.email(), user.name()));
    }
}
