FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
EXPOSE 9030
CMD ["python", "-m", "openfinance_mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "9030"]
