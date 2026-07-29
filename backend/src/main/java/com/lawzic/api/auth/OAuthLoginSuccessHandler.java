package com.lawzic.api.auth;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.client.authentication.OAuth2AuthenticationToken;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.stereotype.Component;
import org.springframework.web.util.UriComponentsBuilder;

import java.io.IOException;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class OAuthLoginSuccessHandler implements AuthenticationSuccessHandler {
    private final OAuthLoginService service;
    @Value("${app.frontend-url:http://localhost:5173}") private String frontendUrl;

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response,
                                        Authentication authentication) throws IOException, ServletException {
        try {
            OAuth2AuthenticationToken token = (OAuth2AuthenticationToken) authentication;
            String provider = token.getAuthorizedClientRegistrationId();
            OAuth2User principal = token.getPrincipal();
            Profile profile = profile(provider, principal);
            String ticket = service.issueTicket(provider, profile.id(), profile.email(), profile.name());
            response.sendRedirect(UriComponentsBuilder.fromUriString(frontendUrl + "/oauth/callback")
                    .queryParam("ticket", ticket).build(true).toUriString());
        } catch (RuntimeException exception) {
            response.sendRedirect(UriComponentsBuilder.fromUriString(frontendUrl + "/oauth/callback")
                    .queryParam("error", "소셜 계정 이메일을 확인할 수 없습니다. 이메일 제공 동의 후 다시 시도하세요.")
                    .build().encode().toUriString());
        }
    }

    @SuppressWarnings("unchecked")
    private Profile profile(String provider, OAuth2User principal) {
        if ("google".equals(provider)) {
            Object verified = principal.getAttributes().get("email_verified");
            if (!(principal instanceof OidcUser) || !Boolean.TRUE.equals(verified)) {
                throw new IllegalArgumentException("Google 이메일 인증이 필요합니다.");
            }
            return required(principal.getAttribute("sub"), principal.getAttribute("email"),
                    principal.getAttribute("name"));
        }
        Map<String, Object> response = (Map<String, Object>) principal.getAttributes().get("response");
        if (response == null) throw new IllegalArgumentException("네이버 사용자 정보를 확인할 수 없습니다.");
        return required(string(response.get("id")), string(response.get("email")), string(response.get("name")));
    }

    private Profile required(String id, String email, String name) {
        if (id == null || email == null || email.isBlank()) {
            throw new IllegalArgumentException("소셜 계정에서 이메일 제공 동의가 필요합니다.");
        }
        return new Profile(id, email.trim().toLowerCase(), name == null || name.isBlank() ? "LAWZIC 사용자" : name);
    }
    private String string(Object value) { return value == null ? null : value.toString(); }
    private record Profile(String id, String email, String name) {}
}
