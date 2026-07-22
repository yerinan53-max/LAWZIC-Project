package com.lawzic.api.auth;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public final class AuthDtos {
    private AuthDtos() {}
    public record SignupRequest(@Email @NotBlank String email,
                                @Size(min = 8, max = 72) String password,
                                @NotBlank @Size(max = 50) String name) {}
    public record LoginRequest(@Email @NotBlank String email, @NotBlank String password) {}
    public record AuthResponse(String accessToken, String tokenType, long expiresIn, UserResponse user) {}
    public record UserResponse(Long id, String email, String name) {}
}
