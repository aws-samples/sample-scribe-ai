import logging
import os
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, ListFlowable, ListItem
from reportlab.lib.units import inch


def generate_pdf(data=None, output_filename=None):
    """
    Generate a nicely formatted PDF document based on the provided data structure

    Args:
        data (dict): The hierarchical data structure for the PDF content
        output_filename (str, optional): The name of the output PDF file. If None, returns PDF as bytes.

    Returns:
        bytes: The PDF content as bytes if output_filename is None
        str: The absolute path to the generated PDF file if output_filename is provided
    """

    logging.info("Generating PDF")

    # Set up page settings
    page_size = letter
    margins = {
        "top": 72,
        "bottom": 72,
        "left": 72,
        "right": 72
    }

    # Apply custom page settings if provided
    if "page_settings" in data:
        page_settings = data["page_settings"]

        # Set page size
        if "page_size" in page_settings:
            page_size_name = page_settings["page_size"].lower()
            if page_size_name == "a4":
                from reportlab.lib.pagesizes import A4
                page_size = A4
            # Add more page sizes as needed

        # Set margins
        if "margin_top" in page_settings:
            margins["top"] = page_settings["margin_top"]
        if "margin_bottom" in page_settings:
            margins["bottom"] = page_settings["margin_bottom"]
        if "margin_left" in page_settings:
            margins["left"] = page_settings["margin_left"]
        if "margin_right" in page_settings:
            margins["right"] = page_settings["margin_right"]

    # Create buffer for PDF content if no output file specified
    buffer = io.BytesIO()

    # Create the PDF document (either to file or buffer)
    doc = SimpleDocTemplate(
        output_filename if output_filename else buffer,
        pagesize=page_size,
        rightMargin=margins["right"],
        leftMargin=margins["left"],
        topMargin=margins["top"],
        bottomMargin=margins["bottom"]
    )

    # Container for the 'Flowable' objects
    elements = []

    # Get styles
    styles = getSampleStyleSheet()

    # Define custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.darkblue,
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.darkblue,
        spaceAfter=12
    )

    heading_styles = {
        1: ParagraphStyle(
            'Heading1',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.darkblue,
            spaceAfter=10
        ),
        2: ParagraphStyle(
            'Heading2',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.darkblue,
            spaceAfter=8
        ),
        3: ParagraphStyle(
            'Heading3',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=6
        )
    }

    normal_style = styles["Normal"]

    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        leftIndent=20,
        firstLineIndent=0,
        spaceBefore=5,
        bulletIndent=0,
        bulletFontName='Helvetica',
        bulletFontSize=10
    )

    # Add title if provided
    if "title" in data:
        elements.append(Paragraph(data["title"], title_style))
        elements.append(Spacer(1, 0.25*inch))

    # Add subtitle if provided
    if "subtitle" in data:
        elements.append(Paragraph(data["subtitle"], subtitle_style))
        elements.append(Spacer(1, 0.25*inch))

    # Add author and date if provided
    if "author" in data or "date" in data:
        author_date = []
        if "author" in data:
            author_date.append(f"Author: {data['author']}")
        if "date" in data:
            author_date.append(f"Date: {data['date']}")

        elements.append(Paragraph(" | ".join(author_date), styles["Italic"]))
        elements.append(Spacer(1, 0.25*inch))

    # Process sections
    for section in data.get("sections", []):
        # Add section heading
        heading = section["heading"]
        level = section.get("level", 1)
        if level not in heading_styles:
            level = 1

        elements.append(Paragraph(heading, heading_styles[level]))
        elements.append(Spacer(1, 0.15*inch))

        # Process content elements
        for content in section.get("content", []):
            content_type = content["type"]

            # Handle different content types
            if content_type == "paragraph":
                # Create paragraph style with custom formatting if provided
                para_style = normal_style
                if "style" in content:
                    style_props = content["style"]
                    custom_style = ParagraphStyle(
                        'CustomParagraph',
                        parent=normal_style
                    )

                    if "font_name" in style_props:
                        custom_style.fontName = style_props["font_name"]
                    if "font_size" in style_props:
                        custom_style.fontSize = style_props["font_size"]
                    if "alignment" in style_props:
                        alignment = style_props["alignment"]
                        if alignment == "center":
                            custom_style.alignment = 1
                        elif alignment == "right":
                            custom_style.alignment = 2
                        elif alignment == "justify":
                            custom_style.alignment = 4
                    if "color" in style_props:
                        color_name = style_props["color"]
                        if hasattr(colors, color_name):
                            custom_style.textColor = getattr(
                                colors, color_name)
                        elif color_name.startswith("#"):
                            from reportlab.lib.colors import HexColor
                            custom_style.textColor = HexColor(color_name)

                    para_style = custom_style

                elements.append(Paragraph(content["text"], para_style))
                elements.append(Spacer(1, 0.1*inch))

            elif content_type == "bullet_list":
                for item in content.get("items", []):
                    elements.append(Paragraph(f"• {item}", bullet_style))
                elements.append(Spacer(1, 0.1*inch))

            elif content_type == "table":
                table_data = content.get("table_data", [])
                if table_data:
                    # Calculate column widths
                    num_cols = len(table_data[0]) if table_data else 0
                    col_width = 6.5 * inch / num_cols if num_cols > 0 else 1 * inch

                    # Use custom width if provided
                    if "width" in content:
                        col_width = content["width"] * inch / num_cols

                    col_widths = [col_width] * num_cols

                    # Create table
                    table = Table(table_data, colWidths=col_widths)

                    # Default table style
                    table_style = TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ])

                    # Apply custom style if provided
                    if "style" in content:
                        style_props = content["style"]
                        if "background" in style_props:
                            bg_color = style_props["background"]
                            if hasattr(colors, bg_color):
                                table_style.add(
                                    'BACKGROUND', (0, 1), (-1, -1), getattr(colors, bg_color))
                            elif bg_color.startswith("#"):
                                from reportlab.lib.colors import HexColor
                                table_style.add(
                                    'BACKGROUND', (0, 1), (-1, -1), HexColor(bg_color))

                    table.setStyle(table_style)
                    elements.append(table)
                    elements.append(Spacer(1, 0.2*inch))

            elif content_type == "image":
                if "image_path" in content:
                    img_path = content["image_path"]
                    img_width = content.get("width", 4) * inch
                    img_height = content.get("height", None)

                    try:
                        if img_height:
                            img = Image(img_path, width=img_width,
                                        height=img_height * inch)
                        else:
                            img = Image(img_path, width=img_width)

                        elements.append(img)
                        elements.append(Spacer(1, 0.2*inch))
                    except Exception as e:
                        logging.error(f"Error adding image {img_path}: {e}")

            elif content_type == "spacer":
                height = content.get("height", 0.25) * inch
                elements.append(Spacer(1, height))

    # Build the PDF
    doc.build(elements)

    # Return bytes if no output file was specified
    if not output_filename:
        pdf_data = buffer.getvalue()
        buffer.close()
        logging.info("PDF generated successfully as bytes")
        return pdf_data
    else:
        logging.info(
            f"PDF generated successfully: {os.path.abspath(output_filename)}")
        return os.path.abspath(output_filename)
