import io

import pdfrw
from reportlab.pdfgen import canvas


def run():
    path_to_template = './CertifiedProfessional-WithForm.pdf'

    user_data = {
        'full_name': 'Mark Needham',
        'date': "17th August 2017",
        'certificate_id': "9549823"
    }

    canvas_data = populate_form_fields(path_to_template, user_data)
    form = merge(canvas_data, template_path=path_to_template)
    save(form, filename="/tmp/{0}.pdf".format(user_data["certificate_id"]))

def merge(overlay_canvas: io.BytesIO, template_path: str) -> io.BytesIO:
    template_pdf = pdfrw.PdfReader(template_path)
    overlay_pdf = pdfrw.PdfReader(overlay_canvas)
    for page, data in zip(template_pdf.pages, overlay_pdf.pages):
        overlay = pdfrw.PageMerge().add(data)[0]
        pdfrw.PageMerge(page).add(overlay).render()
    form = io.BytesIO()
    pdfrw.PdfWriter().write(form, template_pdf)
    form.seek(0)
    return form

def populate_form_fields(path_to_template, user_data) -> io.BytesIO:
    template = pdfrw.PdfReader(path_to_template)
    data = io.BytesIO()
    pdf = canvas.Canvas(data)
    for page in template.Root.Pages.Kids:
        for field in page.Annots:
            label = field.T
            sides_positions = field.Rect
            left = float(min(sides_positions[0], sides_positions[2]))
            bottom = float(min(sides_positions[1], sides_positions[3]))
            value = user_data.get(label.replace("(", "").replace(")", ""), '')
            padding = 10
            line_height = 15

            font = "Helvetica-Bold" if "full_name" in label else "Helvetica"
            font_size = 18 if "certificate_id" in label else 22
            value = "Certificate Id: #{value}".format(value = value) if "certificate_id" in label else value

            pdf.setFont(font, font_size)
            x_middle = (float(sides_positions[2]) - float(sides_positions[0])) / 2 + float(sides_positions[0])
            y_middle = (float(sides_positions[3]) - float(sides_positions[1])) / 2 + float(sides_positions[1])
            pdf.drawCentredString(x=x_middle, y=y_middle, text=value)

        pdf.showPage()
    pdf.save()
    data.seek(0)
    return data

def save(form: io.BytesIO, filename: str):
    with open(filename, 'wb') as f:
        f.write(form.read())

if __name__ == '__main__':
    run()
