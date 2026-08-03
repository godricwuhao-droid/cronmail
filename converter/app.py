"""文档转换微服务 — LibreOffice headless"""
import os
import io
import tempfile
import subprocess
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'doc', 'docx', 'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "document-converter"})


@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({"error": "缺少 file 字段"}), 400

    file = request.files['file']
    filename = file.filename or 'unknown'
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"不支持的文件格式: .{ext}"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, filename)
        file.save(input_path)

        if ext == 'pdf':
            # PDF 直接返回，无需转换
            with open(input_path, 'rb') as f:
                pdf_bytes = f.read()
        else:
            # Word → PDF via LibreOffice
            result = subprocess.run(
                ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', tmpdir, input_path],
                capture_output=True, text=True, timeout=120,
            )
            pdf_name = os.path.splitext(filename)[0] + '.pdf'
            pdf_path = os.path.join(tmpdir, pdf_name)

            if not os.path.exists(pdf_path):
                return jsonify({"error": f"转换失败: {result.stderr}"}), 500

            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=os.path.splitext(filename)[0] + '.pdf',
        )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
