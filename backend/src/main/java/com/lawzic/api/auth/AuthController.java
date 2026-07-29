package com.lawzic.api.auth;

import com.lawzic.api.config.JwtService;
import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import jakarta.validation.Valid;
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
    private final UserRepository users;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AccountService accountService;

    @PostMapping("/signup")
    @ResponseStatus(HttpStatus.CREATED)
    public UserResponse signup(@Valid @RequestBody SignupRequest request) {
        String email = request.email().toLowerCase();
        if (users.existsByEmail(email)) throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 가입된 이메일입니다.");
        User user = users.save(new User(email, passwordEncoder.encode(request.password()), request.name()));
        return toResponse(user);
    }

    @PostMapping("/login")
    public AuthResponse login(@Valid @RequestBody LoginRequest request) {
        User user = users.findByEmail(request.email().toLowerCase())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다."));
        if (!passwordEncoder.matches(request.password(), user.getPasswordHash()))
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다.");
        return new AuthResponse(jwtService.createToken(user.getEmail()), "Bearer", jwtService.expirationSeconds(), toResponse(user));
    }

    @GetMapping("/me")
    public UserResponse me(Principal principal) {
        return toResponse(users.findByEmail(principal.getName()).orElseThrow());
    }

    public record UpdateAccountRequest(String name, String currentPassword, String newPassword) {}

    @PatchMapping("/me")
    public UserResponse updateAccount(
            @RequestBody UpdateAccountRequest request,
            Principal principal
    ) {
        if (request == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "수정할 정보를 입력하세요.");
        return toResponse(accountService.updateAccount(
                principal.getName(),
                request.name(),
                request.currentPassword(),
                request.newPassword()
        ));
    }

    public record DeleteAccountRequest(String password) {}

    @DeleteMapping("/me")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteAccount(
            @RequestBody DeleteAccountRequest request,
            Principal principal
    ) {
        accountService.deleteAccount(
                principal.getName(),
                request == null ? null : request.password()
        );
    }

    private UserResponse toResponse(User user) { return new UserResponse(user.getId(), user.getEmail(), user.getName()); }
}
