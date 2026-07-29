package com.lawzic.api.auth;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.authentication.AuthenticationFailureHandler;
import org.springframework.stereotype.Component;
import org.springframework.web.util.UriComponentsBuilder;

import java.io.IOException;

@Component
public class OAuthLoginFailureHandler implements AuthenticationFailureHandler {
    @Value("${app.frontend-url:http://localhost:5173}") private String frontendUrl;
    @Override
    public void onAuthenticationFailure(HttpServletRequest request, HttpServletResponse response,
                                        AuthenticationException exception) throws IOException {
        response.sendRedirect(UriComponentsBuilder.fromUriString(frontendUrl + "/oauth/callback")
                .queryParam("error", "소셜 로그인에 실패했습니다. 이메일 제공 동의를 확인하고 다시 시도하세요.")
                .build().encode().toUriString());
    }
}
