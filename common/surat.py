
import base64, os, io, datetime
from pathlib import Path
import streamlit as st

ASSETS_DIR = Path(__file__).parent.parent / "assets"

def img_to_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

@st.cache_data
def get_jata_base64():
    return img_to_base64(ASSETS_DIR / "jata_negara.png")

@st.cache_data
def get_tandatangan_base64():
    return img_to_base64(ASSETS_DIR / "tandatangan_pengarah.png")

def render_surat_html_jata(nama, ic, jawatan, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh, tahun):
    jata_b64 = get_jata_base64()
    sign_b64 = get_tandatangan_base64()
    # Fallback kalau takde
    jata_tag = f'<img src="data:image/png;base64,{jata_b64}" style="width:80px;height:auto;">' if jata_b64 else '<div style="font-weight:bold;">JATA NEGARA</div>'
    sign_tag = f'<img src="data:image/png;base64,{sign_b64}" style="width:180px;height:auto;">' if sign_b64 else '<div style="font-family:cursive;font-size:20px;">Pengarah</div>'

    html = f"""
    <html><head><meta charset="utf-8"><style>
    body {{ font-family: 'Times New Roman', serif; font-size:12pt; color:#000; line-height:1.4; }}
    .surat {{ max-width:700px; margin:0 auto; padding:20px; border:1px solid #ccc; }}
    .header {{ text-align:center; margin-bottom:20px; }}
    .header h2 {{ margin:2px; font-size:14pt; }}
    .header h3 {{ margin:2px; font-size:11pt; font-weight:normal; }}
    table.info td {{ padding:4px 8px; vertical-align:top; }}
    .footer {{ margin-top:40px; }}
    .tandatangan {{ display:flex; justify-content:space-between; margin-top:60px; }}
    </style></head><body>
    <div class="surat">
      <div class="header">
        {jata_tag}
        <h2>JABATAN PENDIDIKAN NEGERI SELANGOR</h2>
        <h3>KEMENTERIAN PENDIDIKAN MALAYSIA</h3>
        <p style="font-size:9pt;">Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</p>
        <hr>
      </div>
      <div style="text-align:right; font-size:10pt;">
        Ruj. Kami: {no_surat}<br>Tarikh: {tarikh}
      </div>
      <p><strong>Tuan/Puan {nama}</strong><br>{ic}<br>{sek_asal} - {nama_sek_asal}</p>
      <p>Tuan/Puan,</p>
      <p><strong>PELANTIKAN SEBAGAI {jawatan.upper()} PEPERIKSAAN SPM {tahun}</strong></p>
      <p>Dengan hormatnya saya merujuk kepada perkara di atas.</p>
      <p>2. Sukacita dimaklumkan bahawa tuan/puan telah dilantik sebagai petugas peperiksaan SPM {tahun} seperti berikut:</p>
      <table class="info" border="0">
        <tr><td width="160"><strong>Nama</strong></td><td>: {nama}</td></tr>
        <tr><td><strong>No. IC</strong></td><td>: {ic}</td></tr>
        <tr><td><strong>Jawatan</strong></td><td>: {jawatan}</td></tr>
        <tr><td><strong>Sekolah Asal</strong></td><td>: {sek_asal} - {nama_sek_asal}</td></tr>
        <tr><td><strong>Pusat Ditugaskan</strong></td><td>: {pusat} - {nama_pusat}</td></tr>
        <tr><td><strong>No. Surat</strong></td><td>: {no_surat}</td></tr>
        <tr><td><strong>PPD</strong></td><td>: {kod_ppd} - {ppd_name}</td></tr>
      </table>
      <p>3. Tuan/puan dikehendaki hadir bertugas di pusat peperiksaan yang telah ditetapkan mengikut jadual yang akan dimaklumkan kemudian.</p>
      <p>4. Kerjasama dan komitmen tuan/puan amatlah dihargai dan didahului dengan ucapan terima kasih.</p>
      <p>Sekian, terima kasih.</p>
      <p><strong>"MALAYSIA MADANI"<br>"BERKHIDMAT UNTUK NEGARA"</strong></p>
      <div class="tandatangan">
        <div>
          Saya yang menjalankan amanah,<br><br>
          {sign_tag}<br>
          <strong>Pengarah Pendidikan<br>Jabatan Pendidikan Negeri Selangor</strong>
        </div>
        <div style="text-align:right; font-size:9pt;">
          s.k. Pegawai Pendidikan Daerah<br>PPD {kod_ppd}
        </div>
      </div>
    </div></body></html>
    """
    return html

def html_to_pdf_bytes(html_str):
    try:
        from weasyprint import HTML
        return HTML(string=html_str).write_pdf()
    except:
        pass
    try:
        # fallback reportlab simple
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica", 10)
        y=800
        for line in html_str.split("<"):
            txt = line.split(">")[-1][:90]
            if txt.strip():
                c.drawString(40,y,txt.strip()[:90])
                y-=12
                if y<40:
                    c.showPage()
                    y=800
        c.save()
        return buffer.getvalue()
    except Exception as e:
        return html_str.encode()

def generate_surat_pdf(nama, ic, jawatan, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh, tahun):
    html = render_surat_html_jata(nama, ic, jawatan, sek_asal, nama_sek_asal, pusat, nama_pusat, no_surat, kod_ppd, ppd_name, tarikh, tahun)
    return html_to_pdf_bytes(html)
