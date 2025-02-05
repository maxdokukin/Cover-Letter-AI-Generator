# Use an official Python runtime as a base image
FROM python:3.12

# Set the working directory
WORKDIR /app

# Copy the application and data
COPY . /app

# Install any required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask will run on
EXPOSE 8080

# Define environment variables for Flask
ENV FLASK_APP=app.py

# Run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]