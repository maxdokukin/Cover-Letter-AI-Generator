from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from openai import OpenAI  # Use the client class as shown in your example
import os
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = os.urandom(24)

def load_default_prompt():
    try:
        with open("default_prompt.txt") as f:
            return f.read()
    except Exception:
        return ""

@app.route("/", methods=["GET", "POST"])
def index():
    # Default values for page load
    data = {
        "job_description": "",
        "relevant_info": "",
        "prompt": load_default_prompt(),
        "cover_letter": "",
        "api_key": "",
        "model": "gpt-4o-mini",
        "company_name": ""
    }
    if request.method == "POST":
        # All data is coming from the client (populated via localStorage)
        data["job_description"] = request.form.get("job_description", "")
        data["relevant_info"] = request.form.get("relevant_info", "")
        data["prompt"] = request.form.get("prompt", data["prompt"])
        data["api_key"] = request.form.get("api_key", "")
        data["model"] = request.form.get("model", "gpt-4o-mini")

        if "generate" in request.form:
            if not data["api_key"]:
                flash("API key is not set. Please set it in the API Key section.", "error")
            else:
                # Build full prompt text
                prompt_text = (
                    f"Generate a cover letter using the following information.\n\n"
                    f"Job Description:\n{data['job_description']}\n\n"
                    f"User Relevant Info:\n{data['relevant_info']}\n\n"
                    f"Prompt:\n{data['prompt']}\n"
                    f"current_date: {date.today()}"
                )
                try:
                    client = OpenAI(api_key=data["api_key"])
                    master_role = "user" if data["model"] == "o1-mini" else "system"
                    completion = client.chat.completions.create(
                        model=data["model"],
                        messages=[
                            {"role": master_role, "content": "You are a helpful writer that writes brilliant and brief cover letters."},
                            {"role": "user", "content": prompt_text}
                        ]
                    )
                    cover_letter = completion.choices[0].message.content.strip()
                    data["cover_letter"] = cover_letter

                    # Extract company name from job description
                    extraction_prompt = (
                        "YOU MUST EXTRACT AND RETURN COMPANY NAME FROM THE JOB DESCRIPTION BELOW. YOUR ANSWER MUST ONLY CONTAIN THE COMPANY NAME.\n\n"
                        f"Job Description:\n{data['job_description']}\n\n"
                    )
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a data extractor."},
                            {"role": "user", "content": extraction_prompt}
                        ]
                    )
                    data["company_name"] = completion.choices[0].message.content.strip()
                except Exception as e:
                    flash(f"Error generating cover letter: {e}", "error")
    return render_template("index.html", data=data)

@app.route("/download_pdf", methods=["POST"])
def download_pdf():
    # Since the server is now stateless, the cover letter is passed in the POST form.
    cover_letter = request.form.get("cover_letter", "")
    company_name = request.form.get("company_name", "Unknown Company")
    if not cover_letter:
        flash("No cover letter available to download.", "error")
        return redirect(url_for("index"))
    pdf_buffer = save_pdf(cover_letter)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"Cover Letter - {company_name}.pdf",
        mimetype="application/pdf"
    )

def wrap_text(text, pdf, font_name, font_size, max_width):
    """Wraps text to fit within max_width."""
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current_line = words[0]
        for word in words[1:]:
            if pdf.stringWidth(current_line + " " + word, font_name, font_size) <= max_width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    return lines

def save_pdf(text):
    """Generates a PDF from text and returns a BytesIO buffer."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    font_name = "Times-Roman"
    font_size = 12
    pdf.setFont(font_name, font_size)

    margin = 72
    width, height = letter
    usable_width = width - 2 * margin
    line_height = 14

    lines = wrap_text(text, pdf, font_name, font_size, usable_width)

    y = height - margin
    for line in lines:
        if y < margin:
            pdf.showPage()
            pdf.setFont(font_name, font_size)
            y = height - margin
        pdf.drawString(margin, y, line)
        y -= line_height

    pdf.save()
    buffer.seek(0)
    return buffer

@app.route("/set_api_key", methods=["GET"])
def set_api_key():
    # This page now simply serves the HTML/JS to set values in localStorage.
    return render_template("set_api_key.html")

if __name__ == "__main__":
    app.run(debug=True)
