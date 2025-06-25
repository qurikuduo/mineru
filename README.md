# Mineru: PDF Parsing and OCR Extraction

## 项目简介 / Project Overview

**English**:  
Mineru is a FastAPI-based application designed for parsing PDF, Office, and image files, extracting text and layout information using advanced OCR and document analysis models. It leverages the `magic_pdf` library, PaddleOCR, and YOLO-based models for robust document processing. The project supports both local and S3-based file inputs and outputs results in JSON and Markdown formats. Additionally, a standalone script (`topdf.py`) is included for converting PDFs to Word documents via OCR. 
This project comes from: https://github.com/labring/FastGPT/issues/4652

**中文**:  
Mineru 是一个基于 FastAPI 的应用程序，用于解析 PDF、Office 和图片文件，利用高级 OCR 和文档分析模型提取文本和布局信息。该项目使用 `magic_pdf` 库、PaddleOCR 和基于 YOLO 的模型进行强大的文档处理。支持本地和 S3 文件输入，输出结果为 JSON 和 Markdown 格式。此外，还包括一个独立的脚本（`topdf.py`），用于通过 OCR 将 PDF 转换为 Word 文档。
本项目来源于：https://github.com/labring/FastGPT/issues/4652
---

## 文件结构 / File Structure

```
mineru/
├── app.py                    # FastAPI application for PDF parsing API
├── entrypoint.sh            # Docker entrypoint script
├── Dockerfile               # Docker build configuration
├── magic-pdf.json           # Configuration for models and S3
├── requirements.txt         # Python dependencies
├── download_models.py       # Script to download models from Hugging Face
├── topdf.py                # Script for PDF-to-Word OCR conversion
├── hf-cache/               # Directory for pre-downloaded model weights
└── README.md               # Project documentation
```

---

## 实现方案 / Implementation Details

**English**:  
- **Core Framework**: The project uses FastAPI to provide a RESTful API (`/v2/parse/file`) for parsing files. It supports PDF, Office (.doc, .docx, .ppt, .pptx), and image (.png, .jpg, .jpeg) formats.
- **Document Processing**: The `magic_pdf` library integrates PaddleOCR and YOLO-based models (e.g., `doclayout_yolo`, `yolo_v8_mfd`) for text extraction and layout analysis. Models are pre-loaded at startup to avoid repeated loading.
- **Model Management**: Models are downloaded from Hugging Face (`PDF-Extract-Kit-1.0` and `layoutreader`) and stored in `/opt/models` and `/opt/layoutreader`.
- **Environment**: Built with Python 3.10, CUDA 12.4 for GPU acceleration, and LibreOffice for Office file processing.
- **Standalone Script**: `topdf.py` uses PyMuPDF and PaddleOCR to convert PDFs to images and extract text to Word documents. Note that it reloads PaddleOCR models per file, which can be optimized.

**中文**:  
- **核心框架**：项目使用 FastAPI 提供 RESTful API（`/v2/parse/file`），支持解析 PDF、Office（.doc、.docx、.ppt、.pptx）和图片（.png、.jpg、.jpeg）格式。
- **文档处理**：`magic_pdf` 库集成了 PaddleOCR 和基于 YOLO 的模型（例如 `doclayout_yolo`、`yolo_v8_mfd`），用于文本提取和布局分析。模型在启动时预加载，避免重复加载。
- **模型管理**：模型从 Hugging Face（`PDF-Extract-Kit-1.0` 和 `layoutreader`）下载，存储在 `/opt/models` 和 `/opt/layoutreader`。
- **环境**：基于 Python 3.10，使用 CUDA 12.4 进行 GPU 加速，LibreOffice 用于 Office 文件处理。
- **独立脚本**：`topdf.py` 使用 PyMuPDF 和 PaddleOCR 将 PDF 转换为图片并提取文本到 Word 文档。注意，该脚本每次处理文件时会重新加载 PaddleOCR 模型，可优化。

---

## 使用示例 / Usage Examples

### 1. 运行 Docker 容器 / Running the Docker Container

**English**:  
Build and run the Docker container with GPU support:  
```bash
docker build -t mineru .
docker run -d --gpus all --restart unless-stopped --name mineru -p 18000:8000 mineru
```

**中文**:  
构建并运行带有 GPU 支持的 Docker 容器，使用代理服务器以解决无法访问 `huggingface` 下载模型的问题：  
```bash
docker build \
  --build-arg HTTP_PROXY=http://172.17.0.1:7890 \
  --build-arg HTTPS_PROXY=http://172.17.0.1:7890 \
  --build-arg http_proxy=http://172.17.0.1:7890 \
  --build-arg https_proxy=http://172.17.0.1:7890 \
  -t mineru . > /home/yourname/mineru/build.log 2>&1 &

docker run -d --gpus all --restart unless-stopped --name mineru -p 18000:8000 mineru
```

### 2. 调用 API / Calling the API

**English**:  
Send a POST request to parse a PDF file:  
```bash
curl -X POST "http://localhost:18000/v2/parse/file" -F "file=@/path/to/sample.pdf"
```
Response (example):  
```json
{
  "success": true,
  "message": "",
  "markdown": "![image1.jpg](data:image/jpeg;base64,...)",
  "pages": 2
}
```

*** API document:***
```
http://serverIP:18000/docs
```

**中文**:  
发送 POST 请求解析 PDF 文件：  
```bash
curl -X POST "http://localhost:18000/v2/parse/file" -F "file=@/path/to/sample.pdf"
```
响应（示例）：  
```json
{
  "success": true,
  "message": "",
  "markdown": "![image1.jpg](data:image/jpeg;base64,...)",
  "pages": 2
}
```

*** API 文档：***
```
http://serverIP:18000/docs
```

### 3. 使用 topdf.py / Using topdf.py

**English**:  
Run the standalone script to convert a PDF to a Word document:  
```bash
python topdf.py
```
Ensure the input PDF is in `./pdf_input_dir/`, and outputs will be in `./pdf_output_dir/`.

**中文**:  
运行独立脚本将 PDF 转换为 Word 文档：  
```bash
python topdf.py
```
确保输入 PDF 位于 `./pdf_input_dir/`，输出将保存在 `./pdf_output_dir/`。

---

## 模型文件上传与下载 / Model File Upload and Download

**English**:  
The project requires large model files stored in the `hf-cache/` directory. These files are too large for standard Git storage. The project requires large model files stored in the `hf-cache/` directory, which are too large for standard Git storage. These files are automatically downloaded during the first build. Subsequently, you can extract this folder from the container running the built image: `/opt/`. After extraction, copy all files and subfolders from this folder to the `hf-cache` directory in the project root.

1. Ensure the `hf-cache/` directory is in the project root, as `Dockerfile` copies it to `/opt/` during the build.

**中文**:  
项目需要存储在 `hf-cache/` 目录中的大型模型文件，这些文件对于标准 Git 存储来说过大。第一次编译的时候会自动下载，以后可以从编译后的镜像运行的容器中提取该文件夹：`/opt/`。提取后，将该文件夹中的所有文件和子文件夹拷贝到项目根目录中的`hf-cache`目录。

1. 确保 `hf-cache/` 目录位于项目根目录，`Dockerfile` 会在构建时将其复制到 `/opt/`。

---

## 系统要求 / System Requirements

**English**:  
- **Python**: 3.10
- **CUDA**: 12.4 (for GPU acceleration)
- **Docker**: Required for containerized deployment
- **Dependencies**: See `requirements.txt`
- **Hardware**: GPU recommended for faster model inference

**中文**:  
- **Python**：3.10
- **CUDA**：12.4（用于 GPU 加速）
- **Docker**：用于容器化部署
- **依赖**：见 `requirements.txt`
- **硬件**：建议使用 GPU 以加速模型推理

---

## 许可证 / License

**English**:  
This project is licensed under the MIT License.

**中文**:  
本项目采用 MIT 许可证。

---

## 注意事项 / Notes

**English**:  
- Ensure CUDA 12.4 is installed on the host system for GPU support.
- The `hf-cache/` directory must be properly set up before building the Docker image.
- Optimize `topdf.py` by initializing `PaddleOCR` globally to avoid reloading models per file.

**中文**:  
- 确保主机系统安装了 CUDA 12.4 以支持 GPU。
- 在构建 Docker 镜像前，需正确设置 `hf-cache/` 目录。
- 可通过全局初始化 `PaddleOCR` 优化 `topdf.py`，避免每次处理文件时重新加载模型。
