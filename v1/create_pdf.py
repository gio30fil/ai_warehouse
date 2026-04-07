import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

font_path = os.path.join(BASE_DIR, "fonts", "DejaVuSans.ttf")

pdfmetrics.registerFont(TTFont("DejaVu", font_path))


def create_offer_pdf(products):

    filename = os.path.join(BASE_DIR, "offer.pdf")

    c = canvas.Canvas(filename)

    c.setFont("DejaVu", 18)
    c.drawString(100, 800, "IFSAS - Προσφορά Προϊόντων")

    y = 760

    c.setFont("DejaVu", 12)

    for product in products:

        text = str(product)

        # καθαρισμός περίεργων χαρακτήρων
        text = text.replace("❌", "")
        text = text.replace("\n", "")
        text = text.replace("\r", "")
        text = text.strip()

        c.drawString(100, y, text)

        y -= 25

    c.save()

    return filename