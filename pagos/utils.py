from io import BytesIO
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


def _monto_a_texto(monto):
    """Convierte un monto numérico a texto legible (aprox.)."""
    # Implementación simple sin dependencias externas
    entero = int(monto)
    return f"${entero:,}".replace(',', '.')


def generar_recibo_pdf(pago):
    """
    Genera un recibo PDF en memoria para un pago.
    Retorna un BytesIO listo para descargar.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=1.5 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()

    titulo = ParagraphStyle(
        'Titulo', parent=styles['Heading1'],
        fontSize=20, alignment=TA_CENTER,
        textColor=colors.HexColor('#111827'), spaceAfter=4,
    )
    subtitulo = ParagraphStyle(
        'Subtitulo', parent=styles['Normal'],
        fontSize=11, alignment=TA_CENTER,
        textColor=colors.HexColor('#6b7280'), spaceAfter=20,
    )
    section_title = ParagraphStyle(
        'SectionTitle', parent=styles['Heading2'],
        fontSize=13, textColor=colors.HexColor('#111827'),
        spaceBefore=12, spaceAfter=8,
    )
    normal = styles['Normal']

    elementos = []

    # ===== Encabezado =====
    elementos.append(Paragraph('ARMYLOCK', titulo))
    elementos.append(Paragraph('RECIBO DE PAGO', subtitulo))

    # ===== Información del recibo =====
    info_data = [
        ['N° de recibo:', pago.numero_recibo or '—',
         'Fecha de emisión:', timezone.now().strftime('%d/%m/%Y')],
        ['Período:', pago.periodo_display,
         'Fecha de pago:', pago.fecha_pago.strftime('%d/%m/%Y') if pago.fecha_pago else '—'],
    ]
    info_table = Table(info_data, colWidths=[3.5 * cm, 5 * cm, 3.5 * cm, 5 * cm])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#6b7280')),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(info_table)
    elementos.append(Spacer(1, 20))

    # ===== Datos del alumno =====
    elementos.append(Paragraph('Datos del alumno', section_title))
    alumno = pago.alumno
    alumno_data = [
        ['Nombre:', f'{alumno.nombre} {alumno.apellido}'],
        ['RUT:', alumno.rut],
        ['Cinturón:', f'{alumno.get_cinturon_actual_display()} ({alumno.grados_cinturon}º)'],
        ['Categoría:', alumno.get_categoria_display()],
    ]
    if alumno.tutor_nombre:
        alumno_data.append(['Tutor:', f'{alumno.tutor_nombre} ({alumno.tutor_parentesco})'])

    alumno_table = Table(alumno_data, colWidths=[3.5 * cm, 13.5 * cm])
    alumno_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(alumno_table)
    elementos.append(Spacer(1, 15))

    # ===== Detalle del pago =====
    elementos.append(Paragraph('Detalle del pago', section_title))

    detalle = [
        ['Concepto', 'Monto'],
        [f'Mensualidad - {pago.periodo_display}', f'${pago.monto:,.0f}'],
    ]
    if pago.descuento and pago.descuento > 0:
        detalle.append(['Descuento', f'-${pago.descuento:,.0f}'])

    detalle_table = Table(detalle, colWidths=[12 * cm, 5 * cm])
    detalle_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elementos.append(detalle_table)

    # Total
    total_table = Table(
        [['TOTAL PAGADO', f'${pago.monto_final:,.0f}']],
        colWidths=[12 * cm, 5 * cm],
    )
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#111827')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 13),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elementos.append(total_table)
    elementos.append(Spacer(1, 15))

    # ===== Método de pago =====
    if pago.metodo_pago:
        metodo_texto = pago.get_metodo_pago_display()
        if pago.referencia:
            metodo_texto += f' — Ref: {pago.referencia}'
        elementos.append(Paragraph(
            f'<b>Método de pago:</b> {metodo_texto}', normal
        ))
        elementos.append(Spacer(1, 5))

    if pago.observaciones:
        elementos.append(Paragraph(
            f'<b>Observaciones:</b> {pago.observaciones}', normal
        ))
        elementos.append(Spacer(1, 10))

    # ===== Pie de página =====
    elementos.append(Spacer(1, 30))
    firma_data = [
        ['_________________________', '_________________________'],
        ['Firma del alumno/tutor', 'Firma del instructor'],
    ]
    firma_table = Table(firma_data, colWidths=[8.5 * cm, 8.5 * cm])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#6b7280')),
    ]))
    elementos.append(firma_table)

    # Generar PDF
    doc.build(elementos)
    buffer.seek(0)
    return buffer


def generar_reporte_recaudacion_pdf(pagos, titulo, subtitulo=''):
    """Genera un reporte consolidado de recaudación."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        'Titulo', parent=styles['Heading1'],
        fontSize=18, alignment=TA_CENTER,
        textColor=colors.HexColor('#111827'), spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        'Sub', parent=styles['Normal'],
        fontSize=10, alignment=TA_CENTER,
        textColor=colors.HexColor('#6b7280'), spaceAfter=15,
    )

    elementos = [
        Paragraph('ARMYLOCK', titulo_style),
        Paragraph(titulo, titulo_style),
        Paragraph(subtitulo, sub_style),
    ]

    # Tabla de pagos
    data = [['Fecha', 'Alumno', 'Período', 'Método', 'Monto']]
    total = Decimal('0')
    for p in pagos:
        data.append([
            p.fecha_pago.strftime('%d/%m/%Y') if p.fecha_pago else '—',
            f'{p.alumno.apellido}, {p.alumno.nombre}',
            p.periodo_display,
            p.get_metodo_pago_display() if p.metodo_pago else '—',
            f'${p.monto_final:,.0f}',
        ])
        total += p.monto_final

    data.append(['', '', '', 'TOTAL', f'${total:,.0f}'])

    tabla = Table(
        data,
        colWidths=[2.5 * cm, 6 * cm, 3.5 * cm, 3 * cm, 3 * cm],
        repeatRows=1,
    )
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#111827')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla)

    doc.build(elementos)
    buffer.seek(0)
    return buffer