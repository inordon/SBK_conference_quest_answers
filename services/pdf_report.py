from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import os
from sqlalchemy.orm import Session
from services.analytics import get_event_stats, get_all_events_stats, get_general_stats, calculate_nps, get_word_frequency
import logging

logger = logging.getLogger(__name__)

plt.rcParams['font.family'] = 'DejaVu Sans'
sns.set_style("whitegrid")


class PDFReport:
    """Генератор PDF отчетов"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.doc = SimpleDocTemplate(
            filename, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm
        )
        self.story = []
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        try:
            pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
            font_name = 'DejaVu'
            font_bold = 'DejaVu-Bold'
        except Exception:
            logger.warning("Не удалось загрузить DejaVu шрифт, используется стандартный")
            font_name = 'Helvetica'
            font_bold = 'Helvetica-Bold'
        
        self.styles.add(ParagraphStyle(
            name='CustomTitle', parent=self.styles['Heading1'],
            fontName=font_bold, fontSize=24, textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30, alignment=TA_CENTER))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading', parent=self.styles['Heading2'],
            fontName=font_bold, fontSize=16, textColor=colors.HexColor('#34495E'),
            spaceAfter=12, spaceBefore=12))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody', parent=self.styles['Normal'],
            fontName=font_name, fontSize=11, leading=14, spaceAfter=10))
        
        self.styles.add(ParagraphStyle(
            name='CustomSmall', parent=self.styles['Normal'],
            fontName=font_name, fontSize=9, textColor=colors.grey, alignment=TA_RIGHT))
    
    def add_title(self, text: str):
        self.story.append(Paragraph(text, self.styles['CustomTitle']))
        self.story.append(Spacer(1, 0.5*cm))
    
    def add_heading(self, text: str):
        self.story.append(Paragraph(text, self.styles['CustomHeading']))
    
    def add_paragraph(self, text: str):
        self.story.append(Paragraph(text, self.styles['CustomBody']))
    
    def add_spacer(self, height: float = 0.5):
        self.story.append(Spacer(1, height*cm))
    
    def add_table(self, data: list, col_widths: list = None):
        if not data:
            return
        
        default_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]
        
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle(default_style))
        self.story.append(table)
        self.add_spacer()
    
    def add_chart(self, fig):
        img_buffer = BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        
        img = Image(img_buffer, width=15*cm, height=10*cm)
        self.story.append(img)
        self.add_spacer()
        plt.close(fig)
    
    def add_page_break(self):
        self.story.append(PageBreak())
    
    def build(self):
        self.doc.build(self.story)


def create_rating_distribution_chart(rating_dist: dict):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ratings = list(range(1, 6))
    counts = [rating_dist.get(r, 0) for r in ratings]
    
    colors_list = ['#E74C3C', '#E67E22', '#F39C12', '#2ECC71', '#27AE60']
    bars = ax.bar(ratings, counts, color=colors_list, edgecolor='black', linewidth=1.2)
    
    ax.set_xlabel('Оценка (звезды)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Количество', fontsize=12, fontweight='bold')
    ax.set_title('Распределение оценок', fontsize=14, fontweight='bold')
    ax.set_xticks(ratings)
    
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    return fig


def create_nps_gauge_chart(nps_data: dict):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    nps_value = nps_data['nps']
    
    if nps_value >= 50:
        color = '#27AE60'
    elif nps_value >= 0:
        color = '#F39C12'
    else:
        color = '#E74C3C'
    
    ax1.text(0.5, 0.6, f"{nps_value}%", ha='center', va='center', 
            fontsize=48, fontweight='bold', color=color)
    ax1.text(0.5, 0.35, 'Net Promoter Score', ha='center', va='center', 
            fontsize=14, color='gray')
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    labels = ['Промоутеры', 'Нейтральные', 'Критики']
    sizes = [nps_data['promoters'], nps_data['passives'], nps_data['detractors']]
    colors_pie = ['#27AE60', '#F39C12', '#E74C3C']
    explode = (0.1, 0, 0)
    
    if sum(sizes) > 0:
        ax2.pie(sizes, explode=explode, labels=labels, colors=colors_pie,
               autopct='%1.1f%%', shadow=True, startangle=90)
    ax2.set_title('Распределение пользователей')
    
    plt.tight_layout()
    return fig


def generate_pdf_report(session: Session, event_id: int = None) -> str:
    reports_dir = '/app/reports'
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{reports_dir}/report_{timestamp}.pdf"
    
    pdf = PDFReport(filename)
    
    if event_id:
        stats = get_event_stats(session, event_id)
        
        if not stats:
            raise ValueError(f"Мероприятие {event_id} не найдено")
        
        event = stats['event']
        
        pdf.add_title(f"Отчет по мероприятию")
        pdf.add_heading(event.name)
        
        info_text = f"<b>ID мероприятия:</b> {event.id}<br/>"
        info_text += f"<b>Дата создания:</b> {event.created_at.strftime('%d.%m.%Y %H:%M')}<br/>"
        info_text += f"<b>Статус:</b> {'Активное' if event.status.value == 'active' else 'Завершено'}<br/>"
        if event.closed_at:
            info_text += f"<b>Дата завершения:</b> {event.closed_at.strftime('%d.%m.%Y %H:%M')}<br/>"
        
        pdf.add_paragraph(info_text)
        pdf.add_spacer()
        
        pdf.add_heading("Основные показатели")
        
        metrics_data = [
            ['Метрика', 'Значение'],
            ['Получено отзывов', str(stats['total_feedbacks'])],
            ['Получено оценок', str(stats['total_ratings'])],
            ['Средняя оценка', f"{stats['avg_rating']:.2f}"],
            ['Среднее время ответа', f"{stats['avg_response_time_hours']:.1f} ч."]
        ]
        
        pdf.add_table(metrics_data, col_widths=[8*cm, 8*cm])
        
        if stats['rating_distribution']:
            pdf.add_heading("Распределение оценок")
            chart = create_rating_distribution_chart(stats['rating_distribution'])
            pdf.add_chart(chart)
            
            ratings = [r.rating for r in event.ratings]
            if ratings:
                nps_data = calculate_nps(ratings)
                pdf.add_heading("Net Promoter Score (NPS)")
                chart = create_nps_gauge_chart(nps_data)
                pdf.add_chart(chart)
        
        if stats['top_managers']:
            pdf.add_heading("Топ менеджеров по количеству ответов")
            
            managers_data = [['Менеджер', 'Ответов']]
            for m in stats['top_managers']:
                managers_data.append([m['name'], str(m['count'])])
            
            pdf.add_table(managers_data, col_widths=[12*cm, 4*cm])
    
    else:
        general_stats = get_general_stats(session)
        all_events_stats = get_all_events_stats(session)
        
        pdf.add_title("Общий отчет по обратной связи")
        pdf.add_paragraph(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        pdf.add_spacer()
        
        pdf.add_heading("Общая статистика")
        
        summary_data = [
            ['Показатель', 'Значение'],
            ['Всего мероприятий', str(general_stats['total_events'])],
            ['Активных мероприятий', str(general_stats['active_events'])],
            ['Завершенных мероприятий', str(general_stats['closed_events'])],
            ['Всего отзывов', str(general_stats['total_feedbacks'])],
            ['Всего оценок', str(general_stats['total_ratings'])],
            ['Средняя оценка', general_stats['avg_rating']],
            ['Пользователей', str(general_stats['total_users'])],
            ['Менеджеров', str(general_stats['total_managers'])],
            ['Администраторов', str(general_stats['total_admins'])]
        ]
        
        pdf.add_table(summary_data, col_widths=[10*cm, 6*cm])
        
        if general_stats['top_events']:
            pdf.add_heading("Топ-3 мероприятия по оценкам")
            
            top_data = [['Мероприятие', 'Средняя оценка', 'Оценок']]
            for event in general_stats['top_events']:
                top_data.append([event['name'][:50], f"{event['avg_rating']}", str(event['count'])])
            
            pdf.add_table(top_data, col_widths=[10*cm, 4*cm, 2*cm])
        
        if all_events_stats:
            pdf.add_page_break()
            pdf.add_heading("Детализация по мероприятиям")
            
            for event_stat in all_events_stats[:10]:
                event = event_stat['event']
                
                event_data = [
                    ['Параметр', 'Значение'],
                    ['Название', event.name[:50]],
                    ['Статус', 'Активное' if event.status.value == 'active' else 'Завершено'],
                    ['Отзывов', str(event_stat['total_feedbacks'])],
                    ['Оценок', str(event_stat['total_ratings'])],
                    ['Средняя оценка', f"{event_stat['avg_rating']:.2f}" if event_stat['avg_rating'] else '—']
                ]
                
                pdf.add_table(event_data, col_widths=[8*cm, 8*cm])
                pdf.add_spacer(0.5)
    
    pdf.add_spacer(2)
    footer_text = f"Отчет сгенерирован автоматически | {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    pdf.add_paragraph(f"<i>{footer_text}</i>")
    
    pdf.build()
    
    logger.info(f"PDF отчет сгенерирован: {filename}")
    return filename
