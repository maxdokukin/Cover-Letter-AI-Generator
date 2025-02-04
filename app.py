from flask import Flask, render_template, request, redirect, url_for, flash
from openai import OpenAI  # Use the client class as shown in your example
import os
from datetime import date

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secr

# In-memory storage for user inputs and API key
data_storage = {
    "job_description": "",
    "relevant_info": "",
    "prompt": "",
    "cover_letter": "",
    "api_key": "",
    "model": "chatgpt-4o-latest"  # You can change this as needed
}

@app.route("/", methods=["GET", "POST"])
def index():
    global data_storage

    with open("default_prompt.txt") as f:
        data_storage["prompt"] = f.read()

    if request.method == "POST":
        # Update stored fields from form inputs
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
                    completion = client.chat.completions.create(
                        model=data_storage["model"],
                        messages=[
                            {"role": "system", "content": "You are a helpful writer that writes brilliant and brief cover letters."},
                            {"role": "user", "content": prompt_text}
                        ]
                    )
                    cover_letter = completion.choices[0].message.content.strip()
                    data_storage["cover_letter"] = cover_letter
                except Exception as e:
                    flash(f"Error generating cover letter: {e}", "error")

    return render_template("index.html", data=data_storage)


@app.route("/set_api_key", methods=["GET", "POST"])
def set_api_key():
    global data_storage
    if request.method == "POST":
        api_key = request.form.get("api_key", "")
        if api_key:
            data_storage["api_key"] = api_key
            flash("API key updated successfully.", "success")
            return redirect(url_for("index"))
        else:
            flash("Please enter a valid API key.", "error")
    return render_template("set_api_key.html", data=data_storage)


if __name__ == "__main__":
    app.run(debug=True)
