"""
PDF generation service for reports.
Converts report data to PDF format using reportlab.
"""
from io import BytesIO
from typing import List, Dict, Any
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.pdfgen import canvas


class PDFReportGenerator:
    """Generate PDF reports from data dictionaries."""
    
    def __init__(self, title: str = "Report", page_size=letter):
        """
        Initialize PDF generator.
        
        Args:
            title: Report title
            page_size: Page size (letter or A4)
        """
        self.title = title
        self.page_size = page_size
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()
    
    def _add_custom_styles(self):
        """Add custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=1,  # Center
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2e5090'),
            spaceAfter=12,
            spaceBefore=12,
        ))
    
    def generate_pdf(self, data: List[Dict[str, Any]], report_type: str = "Report") -> bytes:
        """
        Generate PDF from data list.
        
        Args:
            data: List of dictionaries with report data
            report_type: Type of report for title
            
        Returns:
            PDF as bytes
        """
        if not data:
            return self._generate_empty_pdf(report_type)
        
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.page_size,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
        )
        
        story = []
        
        # Add title
        title = Paragraph(f"{report_type} Report", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.3 * inch))
        
        # Add generation timestamp
        timestamp = Paragraph(
            f"<i>Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>",
            self.styles['Normal']
        )
        story.append(timestamp)
        story.append(Spacer(1, 0.2 * inch))
        
        # Add data summary
        summary = Paragraph(f"<b>Total Records: {len(data)}</b>", self.styles['Normal'])
        story.append(summary)
        story.append(Spacer(1, 0.3 * inch))
        
        # Convert data to table
        if data:
            table = self._create_table_from_data(data)
            story.append(table)
        
        # Build PDF
        doc.build(story)
        return self.buffer.getvalue()
    
    def _create_table_from_data(self, data: List[Dict[str, Any]]) -> Table:
        """
        Convert list of dictionaries to ReportLab Table.
        
        Args:
            data: List of dictionaries
            
        Returns:
            ReportLab Table object
        """
        if not data:
            return Table([[Paragraph("No data available", self.styles['Normal'])]])
        
        # Get headers from first record
        headers = list(data[0].keys())
        
        # Create table data: headers + rows
        table_data = [
            [Paragraph(f"<b>{header}</b>", self.styles['Normal']) for header in headers]
        ]
        
        # Add rows
        for row in data:
            row_data = []
            for header in headers:
                value = row.get(header, "")
                # Convert value to string and handle special types
                if isinstance(value, (dict, list)):
                    value = str(value)[:50]  # Truncate complex types
                elif isinstance(value, float):
                    value = f"{value:.2f}"
                elif isinstance(value, bool):
                    value = "Yes" if value else "No"
                
                row_data.append(Paragraph(str(value), self.styles['Normal']))
            table_data.append(row_data)
        
        # Create table
        table = Table(table_data, repeatRows=1)
        
        # Style table
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e5090')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        return table
    
    def _generate_empty_pdf(self, report_type: str) -> bytes:
        """Generate a simple PDF indicating no data."""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.page_size,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )
        
        story = [
            Paragraph(f"{report_type} Report", self.styles['CustomTitle']),
            Spacer(1, 0.3 * inch),
            Paragraph("No data available for this report.", self.styles['Normal']),
        ]
        
        doc.build(story)
        return self.buffer.getvalue()


def generate_report_pdf(data: List[Dict[str, Any]], report_title: str = "Report") -> bytes:
    """
    Convenience function to generate PDF from data.
    
    Args:
        data: List of dictionaries with report data
        report_title: Title for the report
        
    Returns:
        PDF as bytes
    """
    generator = PDFReportGenerator(title=report_title)
    return generator.generate_pdf(data, report_type=report_title)
