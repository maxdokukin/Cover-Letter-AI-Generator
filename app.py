from flask import Flask, render_template, request, redirect, url_for, flash
from openai import OpenAI  # Use the client class as shown in your example
import os
from datetime import date
from io import BytesIO
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secr

# In-memory storage for user inputs and API key
data_storage = {
    "job_description": "",
    "relevant_info": "",
    "prompt": "",
    "cover_letter": "",
    "api_key": "",
    "model": "gpt-4o-mini"  # You can change this as needed
}

@app.route("/", methods=["GET", "POST"])
def index():
    global data_storage

    with open("default_prompt.txt") as f:
        data_storage["prompt"] = f.read()

    if request.method == "POST":
        # Update stored fields from form inputs
        print(f'POST request to OpenAI, using model {data_storage["model"]}')

        prompt = data_storage["prompt"]
        data_storage["job_description"] = request.form.get("job_description", "")
        data_storage["relevant_info"] = request.form.get("relevant_info", "")
        data_storage["prompt"] = request.form.get("prompt", "")

        if "generate" in request.form:
            if not data_storage["api_key"]:
                flash("API key is not set. Please set it at /set_api_key.", "error")
            else:
                # Construct the full prompt
                prompt_text = (
                    f"Generate a cover letter using the following information.\n\n"
                    f"Job Description:\n{data_storage['job_description']}\n\n"
                    f"User Relevant Info:\n{data_storage['relevant_info']}\n\n"
                    f"Prompt:\n{data_storage['prompt']}"
                    f"current_date: {date.today()}"
                )
                try:
                    # Create the client with the API key
                    client = OpenAI(api_key=data_storage["api_key"])
                    # Call the chat completions endpoint using your working example pattern

                    master_role = "user" if data_storage["model"] == "o1-mini" else "system"
                    completion = client.chat.completions.create(
                        model=data_storage["model"],
                        messages=[
                            {"role": master_role, "content": "You are a helpful writer that writes brilliant and brief cover letters."},
                            {"role": "user", "content": prompt_text}
                        ]
                    )
                    cover_letter = completion.choices[0].message.content.strip()
                    data_storage["cover_letter"] = cover_letter

                    prompt_text = (
                        f"YOU MUST EXTRACT AND RETURN COMPANY NAME FROM THE JOB DESCRIPTION BELOW. YOUR ANSWER MUST ONLY CONTAIN THE COMPANY NAME.\n\n"
                        f"Job Description:\n{data_storage['job_description']}\n\n"
                    )
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system",
                             "content": "You are a data extractor."},
                            {"role": "user", "content": prompt_text}
                        ]
                    )
                    data_storage["company_name"] = completion.choices[0].message.content.strip()

                    return redirect(url_for("download_pdf"))
                except Exception as e:
                    flash(f"Error generating cover letter: {e}", "error")

    return render_template("index.html", data=data_storage)


@app.route("/set_api_key", methods=["GET", "POST"])
def set_api_key():
    global data_storage
    if request.method == "POST":
        api_key = request.form.get("api_key", "")
        selected_model = request.form.get("model", "")
        if api_key:
            data_storage["api_key"] = api_key
            if selected_model:
                data_storage["model"] = selected_model
            flash("API key and model updated successfully.", "success")
            return redirect(url_for("index"))
        else:
            flash("Please enter a valid API key.", "error")
    return render_template("set_api_key.html", data=data_storage)


def wrap_text(text, pdf, font_name, font_size, max_width):
    """
    Wraps the input text to fit within max_width.
    Returns a list of lines.
    """
    lines = []
    # Process each paragraph separately (split by newline)
    for paragraph in text.split('\n'):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue

        current_line = words[0]
        for word in words[1:]:
            # Calculate width of the current line if we added the next word
            if pdf.stringWidth(current_line + " " + word, font_name, font_size) <= max_width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    return lines


def save_pdf(text):
    """
    Generates a PDF from the provided text with proper formatting and returns a BytesIO buffer.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    # Set font to Times New Roman at 12pt (ReportLab's built-in font is "Times-Roman")
    font_name = "Times-Roman"
    font_size = 12
    pdf.setFont(font_name, font_size)

    # Define one-inch margins (1 inch = 72 points)
    margin = 72
    width, height = letter
    usable_width = width - 2 * margin
    line_height = 14  # Slightly more than 12pt for readability

    # Wrap the text to the available width
    lines = wrap_text(text, pdf, font_name, font_size, usable_width)

    # Start drawing text from the top margin
    y = height - margin
    for line in lines:
        # Start a new page if we run out of vertical space
        if y < margin:
            pdf.showPage()
            pdf.setFont(font_name, font_size)
            y = height - margin
        pdf.drawString(margin, y, line)
        y -= line_height

    pdf.save()
    buffer.seek(0)
    return buffer


# Example route to trigger the PDF download:
@app.route("/download_pdf")
def download_pdf():
    cover_letter = data_storage.get("cover_letter", "")
    if not cover_letter:
        flash("No cover letter available to download.", "error")
        return redirect(url_for("index"))

    pdf_buffer = save_pdf(cover_letter)
    company_name = data_storage["company_name"]
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"Cover Letter - {company_name}.pdf",
        mimetype="application/pdf"
    )

if __name__ == "__main__":
    app.run(debug=True)
