import Foundation
import Vision
import ImageIO

struct OcrLine: Codable {
    let text: String
    let confidence: Float
    let boundingBox: [Double]
}

struct OcrOutput: Codable {
    let ok: Bool
    let imagePath: String
    let lines: [OcrLine]
    let text: String
    let error: String?
}

func emit(_ output: OcrOutput) {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.withoutEscapingSlashes]
    if let data = try? encoder.encode(output), let json = String(data: data, encoding: .utf8) {
        print(json)
    } else {
        print("{\"ok\":false,\"error\":\"json_encode_failed\"}")
    }
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    emit(OcrOutput(ok: false, imagePath: "", lines: [], text: "", error: "missing_image_path"))
    exit(2)
}

let imagePath = args[1]
let url = URL(fileURLWithPath: imagePath)
guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    emit(OcrOutput(ok: false, imagePath: imagePath, lines: [], text: "", error: "image_load_failed"))
    exit(1)
}

var recognizedLines: [OcrLine] = []
let request = VNRecognizeTextRequest { request, error in
    if let error = error {
        recognizedLines = [
            OcrLine(
                text: "ocr_request_failed: \(error.localizedDescription)",
                confidence: 0,
                boundingBox: []
            )
        ]
        return
    }
    let observations = (request.results as? [VNRecognizedTextObservation]) ?? []
    recognizedLines = observations.compactMap { observation in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        let text = candidate.string.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return nil }
        let box = observation.boundingBox
        return OcrLine(
            text: text,
            confidence: candidate.confidence,
            boundingBox: [
                Double(box.origin.x),
                Double(box.origin.y),
                Double(box.size.width),
                Double(box.size.height)
            ]
        )
    }
}

request.recognitionLevel = VNRequestTextRecognitionLevel.accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["ko-KR", "en-US"]

let handler = VNImageRequestHandler(cgImage: image, options: [:])
do {
    try handler.perform([request])
    let cleanLines = recognizedLines.filter { !$0.text.hasPrefix("ocr_request_failed:") }
    emit(
        OcrOutput(
            ok: true,
            imagePath: imagePath,
            lines: Array(cleanLines.prefix(160)),
            text: cleanLines.map(\.text).joined(separator: "\n"),
            error: nil
        )
    )
} catch {
    emit(OcrOutput(ok: false, imagePath: imagePath, lines: [], text: "", error: error.localizedDescription))
    exit(1)
}
