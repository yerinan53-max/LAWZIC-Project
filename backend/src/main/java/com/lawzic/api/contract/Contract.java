package com.lawzic.api.contract;

import com.lawzic.api.user.User;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Getter
@Entity
@Table(name = "contracts")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Contract {
    public enum Status { UPLOADED, PROCESSING, COMPLETED, FAILED }

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    private User user;
    @Column(nullable = false)
    private String originalFilename;
    @Column(nullable = false, unique = true)
    private String storedFilename;
    @Column(nullable = false)
    private String filePath;
    @Column(nullable = false)
    private long fileSize;
    @Enumerated(EnumType.STRING) @Column(nullable = false)
    private Status status = Status.UPLOADED;
    @Column(nullable = false, updatable = false)
    private Instant uploadedAt = Instant.now();

    public Contract(User user, String originalFilename, String storedFilename, String filePath, long fileSize) {
        this.user = user;
        this.originalFilename = originalFilename;
        this.storedFilename = storedFilename;
        this.filePath = filePath;
        this.fileSize = fileSize;
    }

    public void markProcessing() { status = Status.PROCESSING; }
    public void markCompleted() { status = Status.COMPLETED; }
    public void markFailed() { status = Status.FAILED; }
    public void markUploaded() { status = Status.UPLOADED; }
}
