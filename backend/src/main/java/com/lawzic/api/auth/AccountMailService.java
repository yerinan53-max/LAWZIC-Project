package com.lawzic.api.auth;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AccountMailService {
    private final JavaMailSender mailSender;

    @Value("${app.mail-from:no-reply@lawzic.local}")
    private String from;

    @Value("${app.frontend-url:http://localhost:5173}")
    private String frontendUrl;

    public void sendLoginId(String recipient, String loginId) {
        send(recipient, "[LAWZIC] 가입 이메일 안내",
                "LAWZIC 로그인 아이디는 다음 이메일입니다.\n\n" + loginId +
                        "\n\n본인이 요청하지 않았다면 이 메일을 무시하세요.");
    }

    public void sendPasswordReset(String recipient, String rawToken) {
        String link = frontendUrl + "/reset-password?token=" + rawToken;
        send(recipient, "[LAWZIC] 비밀번호 재설정",
                "아래 링크에서 30분 이내에 비밀번호를 재설정하세요.\n\n" + link +
                        "\n\n본인이 요청하지 않았다면 링크를 열지 마세요.");
    }

    private void send(String recipient, String subject, String body) {
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(from);
        message.setTo(recipient);
        message.setSubject(subject);
        message.setText(body);
        mailSender.send(message);
    }
}
