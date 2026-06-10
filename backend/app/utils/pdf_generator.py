import os
import logging
import asyncio
from io import BytesIO
import markdown
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

logger = logging.getLogger("pdf-generator")


def compile_markdown_to_pdf(content_markdown: str, title: str) -> bytes:
    """Synchronous CPU-bound Markdown to PDF conversion using xhtml2pdf."""
    try:
        # 1. Convert markdown to HTML (enable tables and extra structures)
        html_body = markdown.markdown(
            content_markdown, 
            extensions=['extra', 'tables', 'nl2br']
        )
        
        # 2. Locate templates directory and load memo_template.html
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "templates"
        )
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("memo_template.html")
        
        # 3. Render HTML template with dynamic data
        rendered_html = template.render(
            title=title,
            content_html=html_body
        )
        
        # 4. Compile HTML to PDF in memory
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(
            BytesIO(rendered_html.encode("utf-8")),
            dest=pdf_buffer
        )
        
        if pisa_status.err:
            raise RuntimeError(f"xhtml2pdf compilation error code: {pisa_status.err}")
            
        return pdf_buffer.getvalue()
    except Exception as e:
        logger.error(f"Failed compiling report to PDF: {e}")
        raise


async def generate_report_pdf(content_markdown: str, title: str) -> bytes:
    """Asynchronous wrapper for PDF generation to run in background thread pool."""
    return await asyncio.to_thread(compile_markdown_to_pdf, content_markdown, title)
