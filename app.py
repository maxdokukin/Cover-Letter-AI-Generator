from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from openai import OpenAI  # Use the client class as shown in your example
import os
import uuid
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global in-memory storage for user session data.
# Keys are session IDs and values are dictionaries containing user-specific data.
user_sessions = {}

def get_current_user_data():
    """
    Retrieves or creates the data storage for the current user session.
    """
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    sid = session['session_id']
    if sid not in user_sessions:
        user_sessions[sid] = {
            "job_description": "",
            "relevant_info": "",
            "prompt": "",
            "cover_letter": "",
            "api_key": "",
            "model": "gpt-4o-mini",  # Default model; change as needed
            "company_name": ""
        }
    return user_sessions[sid]

@app.route("/", methods=["GET", "POST"])
def index():
    user_data = get_current_user_data()

    # Read default prompt only if not already set
    if not user_data["prompt"]:
        with open("default_prompt.txt") as f:
            user_data["prompt"] = f.read()

    if request.method == "POST":
        # Update stored fields from form inputs
        print(f'POST request to OpenAI, using model {user_data["model"]}')
        user_data["job_description"] = request.form.get("job_description", "")
        user_data["relevant_info"] = request.form.get("relevant_info", "")
        user_data["prompt"] = request.form.get("prompt", user_data["prompt"])

        if "generate" in request.form:
            if not user_data["api_key"]:
                flash("API key is not set. Please set it at /set_api_key.", "error")
            else:
                # Construct the full prompt
                prompt_text = (
                    f"Generate a cover letter using the following information.\n\n"
                    f"Job Description:\n{user_data['job_description']}\n\n"
                    f"User Relevant Info:\n{user_data['relevant_info']}\n\n"
                    f"Prompt:\n{user_data['prompt']}\n"
                    f"current_date: {date.today()}"
                )
                try:
                    # Create the client with the API key
                    client = OpenAI(api_key=user_data["api_key"])
                    master_role = "user" if user_data["model"] == "o1-mini" else "system"
                    completion = client.chat.completions.create(
                        model=user_data["model"],
                        messages=[
                            {"role": master_role, "content": "You are a helpful writer that writes brilliant and brief cover letters."},
                            {"role": "user", "content": prompt_text}
                        ]
                    )
                    cover_letter = completion.choices[0].message.content.strip()
                    user_data["cover_letter"] = cover_letter

                    # Extract the company name from the job description
                    extraction_prompt = (
                        "YOU MUST EXTRACT AND RETURN COMPANY NAME FROM THE JOB DESCRIPTION BELOW. YOUR ANSWER MUST ONLY CONTAIN THE COMPANY NAME.\n\n"
                        f"Job Description:\n{user_data['job_description']}\n\n"
                    )
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a data extractor."},
                            {"role": "user", "content": extraction_prompt}
                        ]
                    )
                    user_data["company_name"] = completion.choices[0].message.content.strip()

                    return redirect(url_for("download_pdf"))
                except Exception as e:
                    flash(f"Error generating cover letter: {e}", "error")

    return render_template("index.html", data=user_data)

@app.route("/set_api_key", methods=["GET", "POST"])
def set_api_key():
    user_data = get_current_user_data()
    if request.method == "POST":
        api_key = request.form.get("api_key", "")
        selected_model = request.form.get("model", "")
        if api_key:
            user_data["api_key"] = api_key
            if selected_model:
                user_data["model"] = selected_model
            flash("API key and model updated successfully.", "success")
            return redirect(url_for("index"))
        else:
            flash("Please enter a valid API key.", "error")
    return render_template("set_api_key.html", data=user_data)

def wrap_text(text, pdf, font_name, font_size, max_width):
    """
    Wraps the input text to fit within max_width.
    Returns a list of lines.
    """
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
    """
    Generates a PDF from the provided text with proper formatting and returns a BytesIO buffer.
    """
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

@app.route("/download_pdf")
def download_pdf():
    user_data = get_current_user_data()
    cover_letter = user_data.get("cover_letter", "")
    if not cover_letter:
        flash("No cover letter available to download.", "error")
        return redirect(url_for("index"))

    pdf_buffer = save_pdf(cover_letter)
    company_name = user_data.get("company_name", "Unknown Company")
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"Cover Letter - {company_name}.pdf",
        mimetype="application/pdf"
    )

if __name__ == "__main__":
    app.run(debug=True)
