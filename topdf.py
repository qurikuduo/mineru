import fitz
from tqdm import tqdm
import os
from paddleocr import PaddleOCR
from docx import Document  # 用于创建 Word 文档
from docx.shared import Pt  # 设置字体大小
from doc_to_pdf import docx_to_pdf
import shutil
 
def pdf_to_png(pdf_path, img_path,parts_per_page=4):
    """
    将 PDF 每页分割为更多图片
    :param pdf_path: PDF 文件路径
    :param img_path: 输出图片目录
    :param parts_per_page: 每页分割成的图片数量
    """
    # 确保图片输出目录存在
    os.makedirs(img_path, exist_ok=True)
 
    # 打开 PDF 文件
    pdf_doc = fitz.open(pdf_path)
    cnt = 0 
    
    # 遍历每一页
    for pg in tqdm(range(pdf_doc.page_count), total=pdf_doc.page_count, desc='PDF分割处理'):
        page = pdf_doc[pg]
        page_width = page.rect.width  # 页面宽度
        page_height = page.rect.height  # 页面高度
 
        # 计算分割的高度
        split_height = page_height / parts_per_page
 
        for part in range(parts_per_page):
            # 定义裁剪区域
            clip_rect = fitz.Rect(0, split_height * part, page_width, split_height * (part + 1))
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), clip=clip_rect, alpha=False)
            cnt += 1
            # 保存为 PNG 图片
            part_img_path = os.path.join(img_path, f"img_{cnt}.png")
            pix.save(part_img_path)
    
    print(f"PDF分割完成，图片保存在：{img_path}")

# 初始化 OCR 模型，避免在循环中重复加载
det = r"/home/ialover/document/PaddleOCR-release-2.6.1/model/ch_PP-OCRv4_det_infer"
rec = r"/home/ialover/document/PaddleOCR-release-2.6.1/model/ch_PP-OCRv4_rec_infer"
ocr = PaddleOCR(use_angle_cls=True, rec_model_dir=rec, det_model_dir=det,lang = 'ch')

def traversal_file(pdf_name,img_path, out_path):

    # 创建一个新的 Word 文档
    document = Document()
 
    # 设置中文字体（如果需要）
    from docx.oxml.ns import qn
    style = document.styles['Normal']
    font = style.font
    font.name = 'SimSun'  # 宋体
    font.size = Pt(12)
    font.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
 
    # 遍历所有图片文件并进行 OCR 识别
    image_files = sorted(os.listdir(img_path), key=lambda x: int(x.split('_')[1].split('.')[0]))
    for fp in tqdm(image_files, desc='OCR识别处理中'):
        file_path = os.path.join(img_path, fp)
        ocr_result = ocr.ocr(file_path, cls=True)
        # 将识别结果写入 Word 文档
        for one_content in ocr_result[0]:  # 访问第一页内容
            # print(one_content)
            text, confidence = one_content[1]  # 提取文字内容和置信度
            document.add_paragraph(text)  # 仅写入文字内容
    
    # 保存 Word 文档
    output_docx = os.path.join(out_path, f'{pdf_name}.docx')
    document.save(output_docx)
    print(f'OCR 结果已保存到 {output_docx}')
 
def remove_dir(input_path):
    for fg in os.listdir(input_path):
        file_path = os.path.join(input_path, fg)
        if os.path.isfile(file_path):
            os.remove(file_path)
 
def doctopdf(pdf_input_dir,pdf_book_dir):
    for fp in os.listdir(pdf_input_dir):
        file_pdf = os.path.join(pdf_input_dir,fp)
        target_pdf_file = os.path.join(pdf_book_dir,fp)
        if file_pdf.endswith('.pdf'):
            shutil.move(file_pdf,target_pdf_file)
        else:
            docx_to_pdf(file_pdf,pdf_book_dir)
            
def deal_with_pdf_dir(pdf_book_dir,img_path,pdf_output_dir):
    for fp in os.listdir(pdf_book_dir):
        file_path = os.path.join(pdf_book_dir,fp)
        pdf_to_png(file_path,img_path)
        file_name_with_ext = os.path.basename(file_path)
        pdf_name = os.path.splitext(file_name_with_ext)[0]
        traversal_file(pdf_name=pdf_name,img_path=img_path,out_path=pdf_output_dir)
 
 
 
if __name__ == "__main__":
    img_path = "./pdf_img_dir/"  
    pdf_input_dir = './pdf_input_dir'
    pdf_book_dir = './pdf_book_dir/'
    out_path = './pdf_output_dir'
    os.makedirs(out_path,exist_ok=True)
    doctopdf(pdf_input_dir=pdf_input_dir,pdf_book_dir=pdf_book_dir)
    deal_with_pdf_dir(pdf_book_dir=pdf_book_dir,img_path=img_path,pdf_output_dir=out_path)
    remove_dir(img_path)
    remove_dir(pdf_input_dir)
    remove_dir(pdf_book_dir)
