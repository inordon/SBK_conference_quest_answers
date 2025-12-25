from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Безголовый режим для Docker
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import os
from sqlalchemy.orm import Session
from services.analytics import (
    get_event_stats, 
    get_all_events_stats, 
    get_general_stats,
    calculate_nps,
    get_word_frequency
)
from wordcloud import WordCloud
import logging

logger = logging.getLogger(__name__)

# Настройка matplotlib для русского языка
plt.rcParams['font.family'] = 'DejaVu Sans'
sns.set_style("whitegrid")

class PDFReport:
    """Генератор PDF отчетов"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        self.story = []
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        """Настройка стилей для русского текста"""
        # Регистрируем шрифт с поддержкой кириллицы
        try:
            # Попытка использовать системный шрифт
            pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        except:
            logger.warning("Не удалось загрузить DejaVu шрифт, используется стандартный")
        
        # Создаем кастомные стили
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontName='DejaVu-Bold',
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontName='DejaVu-Bold',
            fontSize=16,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontName='DejaVu',
            fontSize=11,
            leading=14,
            spaceAfter=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomSmall',
            parent=self.styles['Normal'],
            fontName='DejaVu',
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_RIGHT
        ))
    
    def add_title(self, text: str):
        """Добавить заголовок"""
        self.story.append(Paragraph(text, self.styles['CustomTitle']))
        self.story.append(Spacer(1, 0.5*cm))
    
    def add_heading(self, text: str):
        """Добавить подзаголовок"""
        self.story.append(Paragraph(text, self.styles['CustomHeading']))
    
    def add_paragraph(self, text: str):
        """Добавить параграф"""
        self.story.append(Paragraph(text, self.styles['CustomBody']))
    
    def add_spacer(self, height: float = 0.5):
        """Добавить отступ"""
        self.story.append(Spacer(1, height*cm))
    
    def add_table(self, data: list, col_widths: list = None, style_list: list = None):
        """Добавить таблицу"""
        if not data:
            return
        
        default_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVu-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'DejaVu'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]
        
        if style_list:
            default_style.extend(style_list)
        
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle(default_style))
        self.story.append(table)
        self.add_spacer()
    
    def add_chart(self, fig):
        """Добавить график matplotlib"""
        img_buffer = BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        
        img = Image(img_buffer, width=15*cm, height=10*cm)
        self.story.append(img)
        self.add_spacer()
        plt.close(fig)
    
    def add_page_break(self):
        """Добавить разрыв страницы"""
        self.story.append(PageBreak())
    
    def build(self):
        """Сгенерировать PDF"""
        self.doc.build(self.story)

def create_rating_distribution_chart(rating_dist: dict) -> plt.Figure:
    """Создать график распределения оценок"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ratings = list(range(1, 6))
    counts = [rating_dist.get(r, 0) for r in ratings]
    
    colors_list = ['#E74C3C', '#E67E22', '#F39C12', '#2ECC71', '#27AE60']
    bars = ax.bar(ratings, counts, color=colors_list, edgecolor='black', linewidth=1.2)
    
    ax.set_xlabel('Оценка (звезды)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Количество', fontsize=12, fontweight='bold')
    ax.set_title('Распределение оценок', fontsize=14, fontweight='bold')
    ax.set_xticks(ratings)
    ax.set_xticklabels(['⭐' * i for i in ratings])
    
    # Добавляем значения над столбцами
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontweight='bold')
    
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    return fig

def create_feedback_timeline_chart(feedbacks_by_day: dict) -> plt.Figure:
    """Создать график динамики обратной связи"""
    if not feedbacks_by_day:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center', fontsize=16)
        return fig
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    dates = sorted(feedbacks_by_day.keys())
    counts = [feedbacks_by_day[d] for d in dates]
    
    ax.plot(dates, counts, marker='o', linewidth=2, markersize=8, color='#3498DB')
    ax.fill_between(dates, counts, alpha=0.3, color='#3498DB')
    
    ax.set_xlabel('Дата', fontsize=12, fontweight='bold')
    ax.set_ylabel('Количество отзывов', fontsize=12, fontweight='bold')
    ax.set_title('Динамика поступления обратной связи', fontsize=14, fontweight='bold')
    
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    return fig

def create_nps_gauge_chart(nps_data: dict) -> plt.Figure:
    """Создать визуализацию NPS"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Gauge chart для NPS
    nps_value = nps_data['nps']
    
    # Определяем цвет на основе NPS
    if nps_value >= 50:
        color = '#27AE60'  # Отлично
    elif nps_value >= 0:
        color = '#F39C12'  # Хорошо
    else:
        color = '#E74C3C'  # Плохо
    
    ax1.text(0.5, 0.6, f"{nps_value}%", ha='center', va='center', 
            fontsize=48, fontweight='bold', color=color)
    ax1.text(0.5, 0.35, 'Net Promoter Score', ha='center', va='center', 
            fontsize=14, color='gray')
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    # Pie chart для распределения
    labels = ['Промоутеры', 'Нейтральные', 'Критики']
    sizes = [nps_data['promoters'], nps_data['passives'], nps_data['detractors']]
    colors_pie = ['#27AE60', '#F39C12', '#E74C3C']
    explode = (0.1, 0, 0)
    
    ax2.pie(sizes, explode=explode, labels=labels, colors=colors_pie,
           autopct='%1.1f%%', shadow=True, startangle=90)
    ax2.set_title('Распределение пользователей')
    
    plt.tight_layout()
    return fig

def create_wordcloud_chart(word_freq: list) -> plt.Figure:
    """Создать облако слов"""
    if not word_freq:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'Недостаточно данных', ha='center', va='center', fontsize=16)
        ax.axis('off')
        return fig
    
    # Создаем словарь частот
    freq_dict = dict(word_freq)
    
    # Генерируем облако слов
    wordcloud = WordCloud(
        width=800, 
        height=400,
        background_color='white',
        colormap='viridis',
        relative_scaling=0.5,
        min_font_size=10
    ).generate_from_frequencies(freq_dict)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    ax.set_title('Ключевые слова из отзывов', fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    return fig

def generate_pdf_report(session: Session, event_id: int = None) -> str:
    """Генерация PDF отчета"""
    
    # Создаем директорию для отчетов
    reports_dir = '/app/reports'
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{reports_dir}/report_{timestamp}.pdf"
    
    pdf = PDFReport(filename)
    
    if event_id:
        # Отчет по конкретному мероприятию
        stats = get_event_stats(session, event_id)
        
        if not stats:
            raise ValueError(f"Мероприятие {event_id} не найдено")
        
        event = stats['event']
        
        # Титульная страница
        pdf.add_title(f"Отчет по мероприятию")
        pdf.add_heading(event.name)
        
        info_text = f"""
        <b>ID мероприятия:</b> {event.id}<br/>
        <b>Дата создания:</b> {event.created_at.strftime('%d.%m.%Y %H:%M')}<br/>
        <b>Статус:</b> {'Активное' if event.status.value == 'active' else 'Завершено'}<br/>
        """
        if event.closed_at:
            info_text += f"<b>Дата завершения:</b> {event.closed_at.strftime('%d.%m.%Y %H:%M')}<br/>"
        
        pdf.add_paragraph(info_text)
        pdf.add_spacer()
        
        # Основные метрики
        pdf.add_heading("📊 Основные показатели")
        
        metrics_data = [
            ['Метрика', 'Значение'],
            ['Получено отзывов', str(stats['total_feedbacks'])],
            ['Получено оценок', str(stats['total_ratings'])],
            ['Средняя оценка', f"{stats['avg_rating']:.2f} ⭐"],
            ['Среднее время ответа', f"{stats['avg_response_time_hours']:.1f} ч."]
        ]
        
        pdf.add_table(metrics_data, col_widths=[8*cm, 8*cm])
        
        # Распределение оценок
        if stats['rating_distribution']:
            pdf.add_heading("⭐ Распределение оценок")
            chart = create_rating_distribution_chart(stats['rating_distribution'])
            pdf.add_chart(chart)
            
            # NPS
            ratings = [r.rating for r in event.ratings]
            if ratings:
                nps_data = calculate_nps(ratings)
                pdf.add_heading("📈 Net Promoter Score (NPS)")
                chart = create_nps_gauge_chart(nps_data)
                pdf.add_chart(chart)
        
        # Динамика обратной связи
        if stats['feedbacks_by_day']:
            pdf.add_page_break()
            pdf.add_heading("📅 Динамика обратной связи")
            chart = create_feedback_timeline_chart(stats['feedbacks_by_day'])
            pdf.add_chart(chart)
        
        # Топ менеджеров
        if stats['top_managers']:
            pdf.add_heading("🏆 Топ менеджеров по количеству ответов")
            
            managers_data = [['Менеджер', 'Ответов']]
            for m in stats['top_managers']:
                managers_data.append([m['name'], str(m['count'])])
            
            pdf.add_table(managers_data, col_widths=[12*cm, 4*cm])
        
        # Облако слов
        word_freq = get_word_frequency(session, event_id=event_id, top_n=50)
        if word_freq:
            pdf.add_page_break()
            pdf.add_heading("☁️ Ключевые слова из отзывов")
            chart = create_wordcloud_chart(word_freq)
            pdf.add_chart(chart)
        
        # Комментарии с низкими оценками
        low_ratings = [c for c in stats['comments'] if c['rating'] <= 2]
        if low_ratings:
            pdf.add_page_break()
            pdf.add_heading("⚠️ Отзывы с низкими оценками")
            
            for comment in low_ratings[:10]:  # Показываем первые 10
                stars = '⭐' * comment['rating']
                date_str = comment['date'].strftime('%d.%m.%Y')
                text = f"<b>{stars}</b> ({date_str})<br/>{comment['comment']}"
                pdf.add_paragraph(text)
                pdf.add_spacer(0.3)
    
    else:
        # Общий отчет по всем мероприятиям
        general_stats = get_general_stats(session)
        all_events_stats = get_all_events_stats(session)
        
        # Титульная страница
        pdf.add_title("Общий отчет по обратной связи")
        pdf.add_paragraph(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        pdf.add_spacer()
        
        # Общая статистика
        pdf.add_heading("📊 Общая статистика")
        
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
        
        # Топ мероприятий
        if general_stats['top_events']:
            pdf.add_heading("🏆 Топ-3 мероприятия по оценкам")
            
            top_data = [['Мероприятие', 'Средняя оценка', 'Оценок']]
            for event in general_stats['top_events']:
                top_data.append([
                    event['name'][:50],
                    f"{event['avg_rating']}⭐",
                    str(event['count'])
                ])
            
            pdf.add_table(top_data, col_widths=[10*cm, 4*cm, 2*cm])
        
        # Детализация по мероприятиям
        pdf.add_page_break()
        pdf.add_heading("📋 Детализация по мероприятиям")
        
        for event_stat in all_events_stats[:10]:  # Первые 10 мероприятий
            event = event_stat['event']
            
            event_data = [
                ['Параметр', 'Значение'],
                ['Название', event.name],
                ['Статус', 'Активное' if event.status.value == 'active' else 'Завершено'],
                ['Отзывов', str(event_stat['total_feedbacks'])],
                ['Оценок', str(event_stat['total_ratings'])],
                ['Средняя оценка', f"{event_stat['avg_rating']:.2f}⭐" if event_stat['avg_rating'] else '—']
            ]
            
            pdf.add_table(event_data, col_widths=[8*cm, 8*cm])
            pdf.add_spacer(0.5)
    
    # Футер
    pdf.add_spacer(2)
    footer_text = f"Отчет сгенерирован автоматически | {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    pdf.add_paragraph(f"<i>{footer_text}</i>")
    
    # Генерируем PDF
    pdf.build()
    
    logger.info(f"PDF отчет сгенерирован: {filename}")
    return filename
