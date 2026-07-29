package com.lawzic.api.auth;

import com.lawzic.api.user.User;
import com.lawzic.api.user.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class OAuthLoginServiceTests {
    @Mock UserRepository users;
    @Mock SocialIdentityRepository identities;
    @Mock OAuthLoginTicketRepository tickets;
    @Mock PasswordEncoder passwordEncoder;

    @Test
    void requiresConsentBeforeCreatingSocialUserWhenEmailIsNew() {
        when(identities.findByProviderAndProviderUserId("google", "subject")).thenReturn(Optional.empty());
        when(users.findByEmail("new@example.com")).thenReturn(Optional.empty());
        when(tickets.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        OAuthLoginService service = new OAuthLoginService(users, identities, tickets, passwordEncoder);

        service.issueTicket("google", "subject", "new@example.com", "새 사용자");

        verify(identities, never()).save(any(SocialIdentity.class));
        verify(users, never()).save(any());
        ArgumentCaptor<OAuthLoginTicket> captor = ArgumentCaptor.forClass(OAuthLoginTicket.class);
        verify(tickets).save(captor.capture());
        assertFalse(captor.getValue().isLinkingRequired());
        assertTrue(captor.getValue().isConsentRequired());
        assertNull(captor.getValue().getUser());
    }

    @Test
    void requiresPasswordLinkInsteadOfAutoMergingSameEmail() {
        User existing = new User("same@example.com", "hash", "기존 사용자");
        when(identities.findByProviderAndProviderUserId("naver", "naver-id")).thenReturn(Optional.empty());
        when(users.findByEmail("same@example.com")).thenReturn(Optional.of(existing));
        when(tickets.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        OAuthLoginService service = new OAuthLoginService(users, identities, tickets, passwordEncoder);

        service.issueTicket("naver", "naver-id", "same@example.com", "사용자");

        verify(identities, never()).save(any());
        ArgumentCaptor<OAuthLoginTicket> captor = ArgumentCaptor.forClass(OAuthLoginTicket.class);
        verify(tickets).save(captor.capture());
        assertTrue(captor.getValue().isLinkingRequired());
        assertNull(captor.getValue().getUser());
    }
}
