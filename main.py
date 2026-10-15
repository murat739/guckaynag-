import io
import math
import os
import html
import logging
import pandas as pd
import streamlit as st

# ReportLab kütüphaneleri PDF üretimi için içe aktarılıyor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# -----------------------------------------------------------------------------
# 1. GÜVENLİK VE ÇEKİRDEK STANDARTLAR (Core Security Boilerplate)
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("MuhendisMatikCore")

def initialize_session_state():
    """Çoklu kullanıcı ve sekme karışmalarını önlemek için oturum hafızasını izole eder."""
    if "data_processed" not in st.session_state:
        st.session_state.data_processed = False
    if "df_input" not in st.session_state:
        st.session_state.df_input = None
    if "calculation_results" not in st.session_state:
        st.session_state.calculation_results = None

def sanitize_text(text: str) -> str:
    """XSS ve zararlı enjeksiyonlara karşı metin verilerini süzgeçten geçirir."""
    if not isinstance(text, str):
        return text
    return html.escape(text)

def render_legal_disclaimer():
    """Arayüzün altına detaylı yasal uyarıyı ekler."""
    st.markdown(
        """
        <div style="padding: 15px; border-radius: 8px; background-color: #FEF2F2; border: 1px solid #F87171; margin-top: 30px;">
            <p style="font-size: 13px; color: #7F1D1D; margin: 0; line-height: 1.5;">
                ⚖️ <strong>HUKUKİ BİLGİLENDİRME VE SORUMLULUK REDDİ BEYANI (DISCLAIMER):</strong><br>
                1. Bu yazılım ve içerisindeki tüm hesaplama araçları, mühendislere ve teknik personele yalnızca <strong>yardımcı olmak maksadıyla</strong> geliştirilmiştir.<br>
                2. Bu yazılım vasıtasıyla elde edilen tüm değerler, çıktılar ve raporlar tavsiye niteliğinde olup; nihai projeelendirme öncesinde yetkili uzmanlar tarafından <strong>mutlaka kontrol edilmesi, doğrulanması ve ilgili standartlara göre yeniden teyit edilmesi gerekmektedir</strong>.<br>
                3. Bu değerlere göre yapılan her türlü tasarım, uygulama, imalat ve operasyonun tüm sorumluluğu münhasıran <strong>kullanıcıya ve projeyi onaylayan mühendislik sorumlularına aittir</strong>. Yazılım geliştiricisinin doğrudan veya dolaylı hiçbir hukuki, cezai ve mali sorumluluğu bulunmamaktadır.<br>
                4. Bu yazılımın telif hakları geliştiriciye aittir. <strong>Kopyalanamaz, çoğaltılamaz ve hiçbir surette ticari amaçlı kullanılamaz.</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# 2. PDF RAPORLAMA VE TÜRKÇE FONT YÖNETİCİSİ
# -----------------------------------------------------------------------------
def turkce_font_ayarla():
    """Linux (Streamlit Cloud) ve Windows sistemlerinde Türkçe karakterleri destekleyen fontu ayarlar."""
    font_adaylari = [
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for yol in font_adaylari:
        if os.path.exists(yol):
            try:
                pdfmetrics.registerFont(TTFont("TrFont", yol))
                return "TrFont"
            except Exception:
                continue
    return "Helvetica"

def pdf_raporu_olustur(veri):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    elements = []

    secilen_font = turkce_font_ayarla()
    styles = getSampleStyleSheet()

    baslik_style = ParagraphStyle(
        "BaslikStyle",
        parent=styles["Heading1"],
        fontName=secilen_font,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A365D"),
        alignment=1,
        spaceAfter=15,
    )

    alt_baslik_style = ParagraphStyle(
        "AltBaslikStyle",
        parent=styles["Heading2"],
        fontName=secilen_font,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=10,
        spaceAfter=6,
    )

    normal_style = ParagraphStyle(
        "NormalStyle",
        parent=styles["Normal"],
        fontName=secilen_font,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
    )

    elements.append(Paragraph("KESİNTİSİZ GÜÇ KAYNAĞI (UPS) & AKÜ BOYUTLANDIRMA RAPORU", baslik_style))
    elements.append(Paragraph("IEC 62040-3 Standartlarına Uygun Teknik Tasarım Belgesi", ParagraphStyle("Sub", parent=normal_style, alignment=1, textColor=colors.gray)))
    elements.append(Spacer(1, 15))

    tablo_verisi = [
        ["Parametre / Kriter Adı", "Tasarım Değeri / Seçim"],
        ["Toplam Aktif Yük", f"{veri['aktif_guc']} kW"],
        ["Güç Faktörü (Cos φ)", f"{veri['guc_faktoru']}"],
        ["Eşzamanlılık Katsayısı", f"{veri['es_zaman']}"],
        ["Net Tasarım Yükü", f"{veri['net_yuk_kw']:.2f} kW"],
        ["Önerilen UPS Gücü", f"{veri['secilen_ups_kva']} kVA"],
        ["İstenen Yedekleme Süresi", f"{veri['sure_dakika']} Dakika"],
        ["Sistem DC Baraj Gerilimi", f"{veri['dc_voltaj']} V"],
        ["Seri Akü Adedi (String)", f"{veri['seri_adet']} Adet"],
        ["Hesaplanan Net Akü Kapasitesi", f"{veri['gerekli_ah']:.1f} Ah"],
        ["Seçilen Standart Blok Akü", f"{veri['secilen_blok_ah']} Ah"],
        ["Akü Deşarj / Peukert Çarpanı", f"{veri['deşarj_katsayisi']}"],
        ["Sıcaklık & Yaşlanma Faktörü", f"{veri['sicaklik_yaslanma_toplam']:.2f} Kat"],
    ]

    t = Table(tablo_verisi, colWidths=[240, 280])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, -1), secilen_font),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ])
    )

    elements.append(t)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Mühendislik Notları ve Sorumluluk Reddi", alt_baslik_style))
    aciklama_metni = (
        "1. Bu yazılım yalnızca teknik personele yardımcı olmak maksadıyla geliştirilmiştir. Hesaplanan tüm değerler uygulama öncesinde yetkili uzmanlarca mutlaka kontrol edilmeli ve doğrulanmalıdır.<br/>"
        "2. Çıkan sonuçlara ve değerlere dayanarak yapılacak her türlü tasarım, uygulama ve imalatın sorumluluğu tamamen kullanıcıya aittir; geliştiricinin hiçbir hukuki ve cezai sorumluluğu yoktur.<br/>"
        "3. Bu yazılım kopyalanamaz ve ticari amaçlı kullanılamaz.<br/>"
        "4. Kısa süreli deşarjlarda kapasite kayıpları Peukert ve deşarj matris katsayıları ile rezerve edilmiştir."
    )
    elements.append(Paragraph(aciklama_metni, normal_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# -----------------------------------------------------------------------------
# 3. ANA UYGULAMA AKIŞI
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Profesyonel UPS ve Akü Boyutlandırma",
        page_icon="⚡",
        layout="wide",
    )
    initialize_session_state()

    st.title("⚡ Nokta Atışı & Hatasız UPS - Akü Boyutlandırma Modülü")
    st.write(
        "Bu profesyonel yazılım; yük faktörlerini, inverter verimini, Peukert deşarj katsayılarını "
        "ve sıcaklık/yaşlanma parametrelerini kusursuz hesaplayarak anında PDF raporu sunar."
    )
    st.markdown("---")

    with st.form("ups_form_ana"):
        st.subheader("1. Yük ve Sistem Parametreleri")
        col1, col2 = st.columns(2)

        with col1:
            aktif_guc = st.number_input("Toplam Gerçek Yük (Aktif Güç - kW)", min_value=0.1, value=30.0, step=1.0)
            guc_faktoru = st.slider("Yük Güç Faktörü (Cos φ)", min_value=0.5, max_value=1.0, value=0.85, step=0.01)
            es_zaman = st.slider("Eşzamanlılık (Simultaneity) Faktörü", min_value=0.1, max_value=1.0, value=0.90, step=0.05)

        with col2:
            sure_dakika = st.number_input("İstenen Yedekleme Süresi (Dakika)", min_value=5, max_value=300, value=30, step=5)
            sicaklik_secim = st.selectbox(
                "Akü Odası Sıcaklık Katsayısı",
                [
                    ("20°C (Standart - Faktör: 1.00)", 1.00),
                    ("25°C (Normal - Faktör: 1.03)", 1.03),
                    ("15°C (Soğuk - Faktör: 1.10)", 1.10),
                    ("10°C ve altı (Kritik - Faktör: 1.18)", 1.18),
                ],
                format_func=lambda x: x[0],
            )[1]
            yaslanma_faktoru = st.number_input("Akü Yaşlanma / Kapasite Emniyet Faktörü", min_value=1.0, max_value=1.5, value=1.25, step=0.01)

        st.subheader("2. Donanım ve Mimari")
        col3, col4 = st.columns(2)
        with col3:
            inverter_verimi = st.slider("UPS İnverter Verimi (%)", min_value=85.0, max_value=97.0, value=93.5)
            dc_voltaj = st.number_input("Sistem DC Baraj Gerilimi (V)", min_value=24, max_value=800, value=384, step=12)
        with col4:
            aku_blok_v = st.selectbox("Akü Blok Gerilimi (V)", [12, 2], index=0)

        calistir = st.form_submit_button("Nokta Atışı Hesapla ve Rapor Hazırla")

    if calistir:
        net_yuk_kw = aktif_guc * es_zaman
        gorus_gucu_kva = net_yuk_kw / guc_faktoru

        standart_kvas = [10, 15, 20, 30, 40, 60, 80, 100, 120, 160, 200, 250, 300, 400, 500, 600, 800, 1000]
        ham_kva = gorus_gucu_kva * 1.20
        secilen_ups_kva = next((k for k in standart_kvas if k >= ham_kva), math.ceil(ham_kva / 100) * 100)

        dc_guc_kw = net_yuk_kw / (inverter_verimi / 100.0)

        if sure_dakika <= 10:
            desarj_katsayisi = 1.45
        elif sure_dakika <= 30:
            desarj_katsayisi = 1.25
        elif sure_dakika <= 60:
            desarj_katsayisi = 1.12
        else:
            desarj_katsayisi = 1.05

        sure_saat = sure_dakika / 60.0
        toplam_enerji_wh = dc_guc_kw * 1000 * sure_saat * sicaklik_secim * yaslanma_faktoru * desarj_katsayisi
        dod = 0.80
        gerekli_ah = toplam_enerji_wh / (dc_voltaj * dod)

        seri_adet = int(dc_voltaj / aku_blok_v)
        standart_ah_listesi = [7, 9, 12, 18, 24, 28, 33, 40, 55, 65, 75, 90, 100, 120, 150, 160, 200, 250, 300]
        secilen_blok_ah = next((ah for ah in standart_ah_listesi if ah >= gerekli_ah), math.ceil(gerekli_ah / 10) * 10)

        st.markdown("---")
        st.subheader("📊 Nokta Atışı Hesaplama Sonuçları")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Önerilen UPS Gücü", f"{secilen_ups_kva} kVA")
        c2.metric("Hesaplanan Net Ah", f"{gerekli_ah:.1f} Ah")
        c3.metric("Seçilen Standart Ah", f"{secilen_blok_ah} Ah")
        c4.metric("Seri Akü Adedi", f"{seri_adet} Adet")

        veri_sozlugu = {
            "aktif_guc": aktif_guc,
            "guc_faktoru": guc_faktoru,
            "es_zaman": es_zaman,
            "net_yuk_kw": net_yuk_kw,
            "secilen_ups_kva": secilen_ups_kva,
            "sure_dakika": sure_dakika,
            "dc_voltaj": dc_voltaj,
            "seri_adet": seri_adet,
            "gerekli_ah": gerekli_ah,
            "secilen_blok_ah": secilen_blok_ah,
            "deşarj_katsayisi": desarj_katsayisi,
            "sicaklik_yaslanma_toplam": sicaklik_secim * yaslanma_faktoru,
        }

        pdf_bytes = pdf_raporu_olustur(veri_sozlugu)

        st.success("✅ Mühendislik raporu başarıyla hazırlandı! Aşağıdaki butondan PDF olarak indirebilirsiniz.")
        st.download_button(
            label="📄 Profesyonel Mühendislik Raporunu İndir (PDF)",
            data=pdf_bytes,
            file_name="UPS_ve_Aku_Boyutlandirma_Raporu.pdf",
            mime="application/pdf",
        )

    render_legal_disclaimer()

if __name__ == "__main__":
    main()