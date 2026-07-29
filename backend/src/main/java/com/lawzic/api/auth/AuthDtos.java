package com.lawzic.api.auth;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public final class AuthDtos {
    private AuthDtos() {}
    public record SignupRequest(@Email @NotBlank String email,
                                @Size(min = 8, max = 72) String password,
                                @NotBlank @Size(max = 50) String name,
                                @AssertTrue(message = "서비스 이용약관 동의는 필수입니다.") boolean termsAgreed,
                                @AssertTrue(message = "개인정보 수집 및 이용 동의는 필수입니다.") boolean privacyAgreed) {}
    public record LoginRequest(@Email @NotBlank String email, @NotBlank String password) {}
    public record AuthResponse(String accessToken, String tokenType, long expiresIn, UserResponse user) {}
    public record UserResponse(Long id, String email, String name) {}
}
