package com.lawzic.api.contract;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.io.File;

@Service
public class PdfTextLayerService {
    private static final int MIN_TEXT_CHARACTERS = 20;
    private static final String SCANNED_PDF_MESSAGE =
            "이 PDF는 스캔 이미지로 구성되어 텍스트를 인식할 수 없습니다. " +
            "LAWZIC은 현재 OCR을 지원하지 않습니다. " +
            "텍스트를 선택·복사할 수 있는 PDF를 업로드해 주세요.";

    public void requireExtractableText(String filePath) {
        try (PDDocument document = Loader.loadPDF(new File(filePath))) {
            String text = new PDFTextStripper().getText(document);
            long meaningfulCharacters = text.codePoints()
                    .filter(Character::isLetterOrDigit)
                    .count();
            if (meaningfulCharacters < MIN_TEXT_CHARACTERS) {
                throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, SCANNED_PDF_MESSAGE);
            }
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new ResponseStatusException(
                    HttpStatus.UNPROCESSABLE_ENTITY,
                    "PDF 텍스트를 확인할 수 없습니다. 올바른 텍스트 기반 PDF인지 확인해 주세요."
            );
        }
    }
}
