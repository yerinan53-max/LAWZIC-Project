package com.lawzic.api.contract;

import lombok.RequiredArgsConstructor;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.rendering.ImageType;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import javax.imageio.ImageIO;
import java.io.ByteArrayOutputStream;
import java.io.File;

@Service
@RequiredArgsConstructor
public class PdfRenderService {
    private final ContractService contracts;

    public byte[] render(Long id, String email, int page) {
        Contract contract = contracts.owned(id, email);
        try (PDDocument document = Loader.loadPDF(new File(contract.getFilePath()))) {
            if (page < 1 || page > document.getNumberOfPages()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "존재하지 않는 PDF 페이지입니다.");
            }
            PDFRenderer renderer = new PDFRenderer(document);
            var image = renderer.renderImageWithDPI(page - 1, 120, ImageType.RGB);
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            ImageIO.write(image, "png", output);
            return output.toByteArray();
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "PDF 페이지를 표시할 수 없습니다.");
        }
    }
}
