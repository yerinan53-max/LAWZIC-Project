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

    public void sendLoginId(String recipient, String loginId) {
        send(recipient, "[LAWZIC] 가입 이메일 안내",
                "LAWZIC 로그인 아이디는 다음 이메일입니다.\n\n" + loginId +
                        "\n\n본인이 요청하지 않았다면 이 메일을 무시하세요.");
    }

    public void sendPasswordReset(String recipient, String verificationCode) {
        send(recipient, "[LAWZIC] 비밀번호 재설정 인증번호",
                "LAWZIC 비밀번호 재설정 인증번호입니다.\n\n" + verificationCode +
                        "\n\n인증번호는 10분 동안 유효합니다. 본인이 요청하지 않았다면 이 메일을 무시하세요.");
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
