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
    if "calculation_results" not in st.session_state:
        st.session_state.calculation_results = None

def render_legal_disclaimer():
    """Arayüzün altına detaylı yasal uyarıyı ekler."""
    st.markdown(
        """
        <div style="padding: 15px; border-radius: 8px; background-color: #FEF2F2; border: 1px solid #F87171; margin-top: 30px;">
            <p style="font-size: 13px; color: #7F1D1D; margin: 0; line-height: 1.5;">
                ⚖️ <strong>HUKUKİ BİLGİLENDİRME VE SORUMLULUK REDDİ BEYANI (DISCLAIMER):</strong><br>
                1. Bu yazılım ve içerisindeki tüm hesaplama araçları, mühendislere ve teknik personele yalnızca <strong>yardımcı olmak maksadıyla</strong> geliştirilmiştir.<br>
                2. Bu yazılım vasıtasıyla elde edilen tüm değerler, çıktılar ve raporlar tavsiye niteliğinde olup; nihai projelendirme öncesinde yetkili uzmanlar tarafından <strong>mutlaka kontrol edilmesi, doğrulanması ve ilgili standartlara göre yeniden teyit edilmesi gerekmektedir</strong>.<br>
                3. Bu değerlere göre yapılan her türlü tasarım, uygulama, imalat ve operasyonun tüm sorumluluğu münhasıran <strong>kullanıcıya ve projeyi onaylayan mühendislik sorumlularına aittir</strong>.<br>
                4. Bu yazılımın telif hakları geliştiriciye aittir. <strong>Kopyalanamaz, çoğaltılamaz ve hiçbir surette ticari amaçlı kullanılamaz.</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# 2. HESAPLAMA ÇEKİRDEĞİ (Core Calculation Engine)
# -----------------------------------------------------------------------------
def hesapla_ups_ve_aku(aktif_guc, guc_faktoru, es_zaman, sure_dakika, sicaklik_secim, yaslanma_faktoru, inverter_verimi, dc_voltaj, aku_blok_v, secilen_blok_ah):
    try:
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

        # Ortalama deşarj gerilimi (EODV kompanzasyonu)
        ortalama_desarj_gerilimi = dc_voltaj * 0.90
        gerekli_ah = toplam_enerji_wh / (ortalama_desarj_gerilimi * dod)

        seri_adet = int(dc_voltaj / aku_blok_v)
        paralel_string_adet = math.ceil(gerekli_ah / secilen_blok_ah)
        toplam_sistem_ah = paralel_string_adet * secilen_blok_ah
        toplam_aku_adedi = seri_adet * paralel_string_adet

        # Fiziksel ve Matematiksel Doğrulama (Assertion Checks)
        assert secilen_ups_kva > 0, "UPS gücü 0'dan büyük olmalı"
        assert gerekli_ah > 0, "Gerekli Ah 0'dan büyük olmalı"
        assert seri_adet > 0, "Seri akü adedi 0 olamaz"
        assert paralel_string_adet > 0, "Paralel kol adedi 0 olamaz"
        assert dc_voltaj % aku_blok_v == 0, "DC baraj gerilimi blok gerilimin katı olmalı"

        sonuclar = {
            "aktif_guc": aktif_guc,
            "guc_faktoru": guc_faktoru,
            "es_zaman": es_zaman,
            "net_yuk_kw": net_yuk_kw,
            "secilen_ups_kva": secilen_ups_kva,
            "sure_dakika": sure_dakika,
            "dc_voltaj": dc_voltaj,
            "aku_blok_v": aku_blok_v,
            "seri_adet": seri_adet,
            "secilen_blok_ah": secilen_blok_ah,
            "paralel_string_adet": paralel_string_adet,
            "toplam_aku_adedi": toplam_aku_adedi,
            "toplam_sistem_ah": toplam_sistem_ah,
            "sicaklik_yaslanma_toplam": sicaklik_secim * yaslanma_faktoru,
        }
        return True, sonuclar
    except Exception as e:
        return False, str(e)

# -----------------------------------------------------------------------------
# 3. PDF RAPORLAMA VE TÜRKÇE FONT YÖNETİCİSİ
# -----------------------------------------------------------------------------
def turkce_karakter_duzelt(metin: str) -> str:
    """Helvetica fontunun desteklemediği Türkçe karakterleri güvenli karakterlere dönüştürür."""
    tr_map = {'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G', 'ı': 'i', 'İ': 'I', 'ö': 'o', 'Ö': 'O', 'ş': 's', 'Ş': 'S', 'ü': 'u', 'Ü': 'U'}
    for k, v in tr_map.items():
        metin = metin.replace(k, v)
    return metin

def turkce_font_ayarla():
    """Linux ve Windows sistemlerinde Türkçe karakterleri destekleyen fontu ayarlar."""
    font_adaylari = ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"]
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
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    secilen_font = turkce_font_ayarla()
    using_fallback = (secilen_font == "Helvetica")
    styles = getSampleStyleSheet()

    baslik_style = ParagraphStyle("BaslikStyle", parent=styles["Heading1"], fontName=secilen_font, fontSize=15, leading=19, textColor=colors.HexColor("#1A365D"), alignment=1, spaceAfter=12)
    alt_baslik_style = ParagraphStyle("AltBaslikStyle", parent=styles["Heading2"], fontName=secilen_font, fontSize=10, leading=14, textColor=colors.HexColor("#2B6CB0"), spaceBefore=8, spaceAfter=4)
    normal_style = ParagraphStyle("NormalStyle", parent=styles["Normal"], fontName=secilen_font, fontSize=8.5, leading=12, textColor=colors.HexColor("#2D3748"))

    baslik_metin = "KESINTISIZ GUC KAYNAGI (UPS) & AKU BOYUTLANDIRMA RAPORU" if using_fallback else "KESİNTİSİZ GÜÇ KAYNAĞI (UPS) & AKÜ BOYUTLANDIRMA RAPORU"
    elements.append(Paragraph(baslik_metin, baslik_style))
    elements.append(Spacer(1, 5))

    ham_tablo_verisi = [
        ["Parametre / Kriter Adı", "Tasarım Değeri / Seçim"],
        ["Toplam Aktif Yük", f"{veri['aktif_guc']} kW"],
        ["Güç Faktörü (Cos φ)", f"{veri['guc_faktoru']}"],
        ["Eşzamanlılık Katsayısı", f"{veri['es_zaman']}"],
        ["Net Tasarım Yükü", f"{veri['net_yuk_kw']:.2f} kW"],
        ["Önerilen UPS Gücü", f"{veri['secilen_ups_kva']} kVA"],
        ["İstenen Yedekleme Süresi", f"{veri['sure_dakika']} Dakika"],
        ["Sistem DC Baraj Gerilimi", f"{veri['dc_voltaj']} V"],
        ["Akü Blok Gerilimi", f"{veri['aku_blok_v']} V"],
        ["Seri Akü Adedi", f"{veri['seri_adet']} Adet"],
        ["Seçilen Blok Akü", f"{veri['secilen_blok_ah']} Ah"],
        ["Paralel Kol Sayısı", f"{veri['paralel_string_adet']} Adet"],
        ["Toplam Akü Adedi", f"{veri['toplam_aku_adedi']} Adet"],
    ]

    tablo_verisi = [[turkce_karakter_duzelt(s[0]) if using_fallback else s[0], turkce_karakter_duzelt(s[1]) if using_fallback else s[1]] for s in ham_tablo_verisi]

    t = Table(tablo_verisi, colWidths=[240, 280])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, -1), secilen_font),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 8))

    uzman_baslik = "Muhendislik ve Uzman Tavsiyeleri" if using_fallback else "Mühendislik ve Uzman Tavsiyeleri"
    elements.append(Paragraph(uzman_baslik, alt_baslik_style))
    
    uzman_metni = (
        "1. <strong>Akü Yerleşimi ve Havalandırma:</strong> Akü gruplarının kurulacağı odanın sıcaklığı 20°C - 25°C arasında tutulmalı ve akü üreticilerinin standardına uygun havalandırma (hidrojen gazı tahliyesi) sağlanmalıdır.<br/>"
        "2. <strong>Kablolama ve Gerilim Düşümü:</strong> Akü dolabı ile UPS arasındaki DC güç kabloları kesiti, akım taşıma kapasitesi ve gerilim düşümü (%1'i geçmeyecek şekilde) gözetilerek seçilmelidir.<br/>"
        "3. <strong>Bakım ve Test:</strong> Akülerin ömrünü uzatmak için periyodik empedans ölçümleri ve yük testleri yapılmalı, üreticinin deşarj performans tablosuyla nihai teyit alınmalıdır."
    )
    if using_fallback:
        uzman_metni = turkce_karakter_duzelt(uzman_metni)

    elements.append(Paragraph(uzman_metni, normal_style))
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# -----------------------------------------------------------------------------
# 4. ANA UYGULAMA AKIŞI
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Profesyonel UPS ve Akü Boyutlandırma", page_icon="⚡", layout="wide")
    initialize_session_state()

    st.title("⚡ Profesyonel UPS ve Akü Boyutlandırma Modülü")
    st.write("Bu yazılım ile yük faktörlerini, inverter verimini ve paralel kol mimarisini dikkate alarak hassas tasarım yapabilirsiniz.")
    st.markdown("---")

    if st.session_state.calculation_results is not None:
        col_info, col_btn = st.columns([3, 1])
        with col_info:
            st.info("💡 Önceki hesaplama sonuçları görüntüleniyor. Yeni bir hesaplama yapmak için butonu kullanabilirsiniz.")
        with col_btn:
            if st.button("🔄 Yeni Hesap", use_container_width=True):
                st.session_state.calculation_results = None
                st.rerun()
        st.markdown("---")

    with st.form("ups_form_ana"):
        st.subheader("1. Yük ve Sistem Parametreleri")
        col1, col2 = st.columns(2)

        with col1:
            aktif_guc = st.number_input("Toplam Gerçek Yük (Aktif Güç - kW)", min_value=0.1, value=30.0, step=1.0)
            guc_faktoru = st.slider("Yük Güç Faktörü (Cos φ)", min_value=0.5, max_value=1.0, value=0.85, step=0.01)
            es_zaman = st.slider("Eşzamanlılık Katsayısı", min_value=0.1, max_value=1.0, value=0.90, step=0.05)

        with col2:
            sure_dakika = st.number_input("İstenen Yedekleme Süresi (Dakika)", min_value=5, max_value=300, value=30, step=5)
            sicaklik_secim = st.selectbox(
                "Akü Odası Sıcaklık Katsayısı",
                [("20°C (Standart - Faktör: 1.00)", 1.00), ("25°C (Normal - Faktör: 1.03)", 1.03), ("15°C (Soğuk - Faktör: 1.10)", 1.10)],
                format_func=lambda x: x[0],
            )[1]
            yaslanma_faktoru = st.number_input("Akü Yaşlanma / Kapasite Emniyet Faktörü", min_value=1.0, max_value=1.5, value=1.25, step=0.01)

        st.subheader("2. Donanım ve Mimari")
        col3, col4 = st.columns(2)
        with col3:
            inverter_verimi = st.slider("UPS İnverter Verimi (%)", min_value=85.0, max_value=97.0, value=93.5)
            dc_voltaj = st.number_input("Sistem DC Baraj Nominal Gerilimi (V)", min_value=12, max_value=800, value=384, step=12)
        with col4:
            # 24V akü seçeneği de eklendi [24, 12, 6, 2]
            aku_blok_v = st.selectbox("Akü Blok Gerilimi (V)", [24, 12, 6, 2], index=1)
            secilen_blok_ah = st.selectbox("Seçilecek Standart Blok Akü Kapasitesi (Ah)", [24, 33, 40, 55, 65, 75, 90, 100, 120, 150, 160, 200], index=7)

        calistir = st.form_submit_button("Hassas Hesapla ve Rapor Hazırla")

    if calistir:
        basari, sonuc = hesapla_ups_ve_aku(
            aktif_guc, guc_faktoru, es_zaman, sure_dakika, 
            sicaklik_secim, yaslanma_faktoru, inverter_verimi, 
            dc_voltaj, aku_blok_v, secilen_blok_ah
        )

        if basari:
            st.session_state.calculation_results = sonuc
            st.rerun()
        else:
            st.error(f"Hata oluştu: {sonuc}")

    if st.session_state.calculation_results is not None:
        sonuc = st.session_state.calculation_results
        st.markdown("---")
        st.subheader("📊 Hesaplama Sonuçları")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Önerilen UPS Gücü", f"{sonuc['secilen_ups_kva']} kVA")
        c2.metric("Sistem Toplam Kapasitesi", f"{sonuc['toplam_sistem_ah']} Ah")
        c3.metric("Paralel Kol Sayısı", f"{sonuc['paralel_string_adet']} Adet")
        c4.metric("Toplam Akü Adedi", f"{sonuc['toplam_aku_adedi']} Adet")

        pdf_bytes = pdf_raporu_olustur(sonuc)
        st.success("✅ Rapor başarıyla hazırlandı!")
        st.download_button(
            label="📄 PDF Raporunu İndir",
            data=pdf_bytes,
            file_name="UPS_ve_Aku_Boyutlandirma_Raporu.pdf",
            mime="application/pdf",
        )

    render_legal_disclaimer()

if __name__ == "__main__":
    main()