import asyncio
import logging
import os
from io import BytesIO

import markdown
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("pdf-generator")


def compile_markdown_to_pdf(content_markdown: str, title: str) -> bytes:
    """Synchronous CPU-bound Markdown to PDF conversion using xhtml2pdf.

    `xhtml2pdf` (via its `bidi` native dependency) can fail to import on some
    Windows machines where an Application Control policy blocks the DLL. Importing
    it lazily here — instead of at module top — keeps that failure contained to the
    (optional, parked) PDF-report path so it can never crash server startup.
    """
    try:
        from xhtml2pdf import pisa  # lazy: see docstring

        html_body = markdown.markdown(content_markdown, extensions=["extra", "tables", "nl2br"])

        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("memo_template.html")

        rendered_html = template.render(title=title, content_html=html_body)

        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(BytesIO(rendered_html.encode("utf-8")), dest=pdf_buffer)

        if pisa_status.err:
            raise RuntimeError(f"xhtml2pdf compilation error code: {pisa_status.err}")

        return pdf_buffer.getvalue()
    except Exception as e:
        logger.error(f"Failed compiling report to PDF: {e}")
        raise


async def generate_report_pdf(content_markdown: str, title: str) -> bytes:
    """Asynchronous wrapper for PDF generation to run in background thread pool."""
    return await asyncio.to_thread(compile_markdown_to_pdf, content_markdown, title)
