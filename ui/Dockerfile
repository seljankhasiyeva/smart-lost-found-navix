FROM python:3.11-slim
WORKDIR /app
COPY app.py .
RUN pip install gradio==4.44.0 requests==2.31.0
EXPOSE 7860
CMD ["python", "app.py"]