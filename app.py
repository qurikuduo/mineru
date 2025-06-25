import json
import os
from base64 import b64encode
from glob import glob
from io import StringIO
import tempfile
from typing import Tuple, Union
import shutil
import re
import imghdr
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from loguru import logger
import base64
from magic_pdf.data.read_api import read_local_images, read_local_office
import magic_pdf.model as model_config
from magic_pdf.config.enums import SupportedPdfParseMethod
from magic_pdf.data.data_reader_writer import DataWriter, FileBasedDataWriter
from magic_pdf.data.data_reader_writer.s3 import S3DataReader, S3DataWriter
from magic_pdf.data.dataset import ImageDataset, PymuDocDataset
from magic_pdf.libs.config_reader import get_bucket_name, get_s3_config
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.operators.models import InferenceResult
from magic_pdf.operators.pipes import PipeResult

model_config.__use_inside_model__ = True

app = FastAPI()

pdf_extensions = [".pdf"]
office_extensions = [".ppt", ".pptx", ".doc", ".docx"]
image_extensions = [".png", ".jpg", ".jpeg"]

class MemoryDataWriter(DataWriter):
    def __init__(self):
        self.buffer = StringIO()

    def write(self, path: str, data: bytes) -> None:
        if isinstance(data, str):
            self.buffer.write(data)
        else:
            self.buffer.write(data.decode("utf-8"))

    def write_string(self, path: str, data: str) -> None:
        self.buffer.write(data)

    def get_value(self) -> str:
        return self.buffer.getvalue()

    def close(self):
        self.buffer.close()


def init_writers(
    file_path: str = None,
    file: UploadFile = None,
    output_path: str = None,
    output_image_path: str = None,
) -> Tuple[
    Union[S3DataWriter, FileBasedDataWriter],
    Union[S3DataWriter, FileBasedDataWriter],
    bytes,
]:
    """
    Initialize writers based on path type

    Args:
        file_path: file path (local path or S3 path)
        file: Uploaded file object
        output_path: Output directory path
        output_image_path: Image output directory path

    Returns:
        Tuple[writer, image_writer, file_bytes]: Returns initialized writer tuple and file content
    """
    file_extension:str = None
    if file_path:
        is_s3_path = file_path.startswith("s3://")
        if is_s3_path:
            bucket = get_bucket_name(file_path)
            ak, sk, endpoint = get_s3_config(bucket)

            writer = S3DataWriter(
                output_path, bucket=bucket, ak=ak, sk=sk, endpoint_url=endpoint
            )
            image_writer = S3DataWriter(
                output_image_path, bucket=bucket, ak=ak, sk=sk, endpoint_url=endpoint
            )
            # 临时创建reader读取文件内容
            temp_reader = S3DataReader(
                "", bucket=bucket, ak=ak, sk=sk, endpoint_url=endpoint
            )
            file_bytes = temp_reader.read(file_path)
            file_extension = os.path.splitext(file_path)[1]
        else:
            writer = FileBasedDataWriter(output_path)
            image_writer = FileBasedDataWriter(output_image_path)
            os.makedirs(output_image_path, exist_ok=True)
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            file_extension = os.path.splitext(file_path)[1]
    else:
        # 处理上传的文件
        file_bytes = file.file.read()
        file_extension = os.path.splitext(file.filename)[1]
        writer = FileBasedDataWriter(output_path)
        image_writer = FileBasedDataWriter(output_image_path)
        os.makedirs(output_image_path, exist_ok=True)

    return writer, image_writer, file_bytes, file_extension


def process_file(
    file_bytes: bytes,
    file_extension: str,
    parse_method: str,
    image_writer: Union[S3DataWriter, FileBasedDataWriter],
) -> Tuple[InferenceResult, PipeResult]:
    """
    Process PDF file content

    Args:
        file_bytes: Binary content of file
        file_extension: file extension
        parse_method: Parse method ('ocr', 'txt', 'auto')
        image_writer: Image writer

    Returns:
        Tuple[InferenceResult, PipeResult]: Returns inference result and pipeline result
    """

    ds: Union[PymuDocDataset, ImageDataset] = None
    if file_extension in pdf_extensions:
        ds = PymuDocDataset(file_bytes)
    elif file_extension in office_extensions:
        # 需要使用office解析
        temp_dir = tempfile.mkdtemp()
        with open(os.path.join(temp_dir, f"temp_file.{file_extension}"), "wb") as f:
            f.write(file_bytes)
        ds = read_local_office(temp_dir)[0]
    elif file_extension in image_extensions:
        # 需要使用ocr解析
        temp_dir = tempfile.mkdtemp()
        with open(os.path.join(temp_dir, f"temp_file.{file_extension}"), "wb") as f:
            f.write(file_bytes)
        ds = read_local_images(temp_dir)[0]
    infer_result: InferenceResult = None
    pipe_result: PipeResult = None

    if parse_method == "ocr":
        infer_result = ds.apply(doc_analyze, ocr=True)
        pipe_result = infer_result.pipe_ocr_mode(image_writer)
    elif parse_method == "txt":
        infer_result = ds.apply(doc_analyze, ocr=False)
        pipe_result = infer_result.pipe_txt_mode(image_writer)
    else:  # auto
        if ds.classify() == SupportedPdfParseMethod.OCR:
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        else:
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)

    return infer_result, pipe_result


def encode_image(image_path):
    """Encode image using base64"""
    with open(image_path, "rb") as image_file:  # 以二进制模式读取 
        image_data = image_file.read()
        return base64.b64encode(image_data).decode('utf-8').replace('\n', '')  # 解码为字符串 
    
def get_mime_type(image_path):
    """动态检测图片MIME类型"""
    img_type = imghdr.what(image_path)
    return f"image/{img_type}" if img_type else "application/octet-stream"

@app.post(
    "/v2/parse/file",
    tags=["projects"],
    summary="Parse files (supports local files and S3)",
)
async def file_parse(
    file: UploadFile = None,
    # file_path: str = None,
    # parse_method: str = "auto",
    # is_json_md_dump: bool = False,
    # output_dir: str = "output",
    # return_layout: bool = False,
    # return_info: bool = False,
    # return_content_list: bool = False,
    # return_images: bool = False, 
    ):
    """
    Execute the process of converting PDF to JSON and MD, outputting MD and JSON files
    to the specified directory.

    Args:
        file: The PDF file to be parsed. Must not be specified together with
            `file_path`
        file_path: The path to the PDF file to be parsed. Must not be specified together
            with `file`
        parse_method: Parsing method, can be auto, ocr, or txt. Default is auto. If
            results are not satisfactory, try ocr
        is_json_md_dump: Whether to write parsed data to .json and .md files. Default
            to False. Different stages of data will be written to different .json files
            (3 in total), md content will be saved to .md file
        output_dir: Output directory for results. A folder named after the PDF file
            will be created to store all results
        return_layout: Whether to return parsed PDF layout. Default to False
        return_info: Whether to return parsed PDF info. Default to False
        return_content_list: Whether to return parsed PDF content list. Default to False
    """
    try:
        output_dir: str = "output"
        parse_method: str = "auto"
        # Get PDF filename
        file_name = os.path.basename(file.filename).split(
            "."
        )[0]
        output_path = f"{output_dir}/{file_name}"
        output_image_path = f"{output_path}/images"


        #total_pages = pdf_document.page_count
        # Initialize readers/writers and get PDF content
        writer, image_writer, file_bytes, file_extension = init_writers(
            #file_path=file_path,
            file=file,
            output_path=output_path,
            output_image_path=output_image_path,
        )

        # Process PDF
        infer_result, pipe_result = process_file(file_bytes, file_extension, parse_method, image_writer)

        # Use MemoryDataWriter to get results
        content_list_writer = MemoryDataWriter()
        md_content_writer = MemoryDataWriter()
        middle_json_writer = MemoryDataWriter()

        # Use PipeResult's dump method to get data
        pipe_result.dump_content_list(content_list_writer, "", "images")
        pipe_result.dump_md(md_content_writer, "", "images")
        pipe_result.dump_middle_json(middle_json_writer, "")

        # Get content
        content_list = json.loads(content_list_writer.get_value())
        md_content = md_content_writer.get_value()
        middle_json = json.loads(middle_json_writer.get_value())
        model_json = infer_result.get_infer_res()

        # If results need to be saved
        # if is_json_md_dump:
        #     writer.write_string(
        #         f"{file_name}_content_list.json", content_list_writer.get_value()
        #     )
        #     writer.write_string(f"{file_name}.md", md_content)
        #     writer.write_string(
        #         f"{file_name}_middle.json", middle_json_writer.get_value()
        #     )
        #     writer.write_string(
        #         f"{file_name}_model.json",
        #         json.dumps(model_json, indent=4, ensure_ascii=False),
        #     )
        #     # Save visualization results
        #     pipe_result.draw_layout(os.path.join(output_path, f"{file_name}_layout.pdf"))
        #     pipe_result.draw_span(os.path.join(output_path, f"{file_name}_spans.pdf"))
        #     pipe_result.draw_line_sort(
        #         os.path.join(output_path, f"{file_name}_line_sort.pdf")
        #     )
        #     infer_result.draw_model(os.path.join(output_path, f"{file_name}_model.pdf"))

        # Build return data
        data = {}
        # if return_layout:
        #     data["layout"] = model_json
        # if return_info:
        #     data["info"] = middle_json
        # if return_content_list:
        #     data["content_list"] = content_list
        # if return_images:
        image_paths = glob(f"{output_image_path}/*.jpg")
        data["images"] = {}
        for image_path in image_paths:
            filename = os.path.basename(image_path)  # 提取文件名 
            mime_type = get_mime_type(image_path)
            base64_str = encode_image(image_path)
            data["images"][filename] = f"data:{mime_type};base64,{base64_str}"  # 完整Data URL

        # 替换Markdown中的图片路径
        def replace_image(match):
            original_path = match.group(1)
            filename = original_path.split('/')[-1]
            if filename in data['images']:
                return f'![{filename}]({data["images"][filename]})'  # 直接使用完整Data URL 
            else:
                return f'![{filename}]({original_path})'

        pattern = re.compile(r'!\[\]\((images/.*?)\)')
        data["md_content"] = pattern.sub(replace_image, md_content)
        

        # Clean up memory writers
        content_list_writer.close()
        md_content_writer.close()
        middle_json_writer.close()

        return {
                "success": True,
                "message": "",
                "markdown": data.get("md_content", ""),
                "pages": len(model_json),
            }
    
        #shutil.rmtree(output_path)

    except Exception as e:
        logger.exception(e)
        return JSONResponse(content={
                "success": False,
                "message": "",
                "error": f"Internal server error: {str(e)}"
            }, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7333)

