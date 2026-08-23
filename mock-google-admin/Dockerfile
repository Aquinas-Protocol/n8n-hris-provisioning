FROM python:3.12-slim
WORKDIR /app
COPY mock_google_admin.py /app/
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/_mock/state')"
CMD ["python", "/app/mock_google_admin.py", "--host", "0.0.0.0", "--port", "8000"]
