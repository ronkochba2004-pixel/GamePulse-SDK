FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir uv

# Copy workspace files needed to resolve the package
COPY pyproject.toml ./
COPY packages/gamepulse-core ./packages/gamepulse-core
COPY apps/dashboard ./apps/dashboard

# Install dashboard + core deps only
RUN uv pip install --system \
    -e ./packages/gamepulse-core \
    "streamlit>=1.36" \
    "plotly>=5.22" \
    "pandas>=2.2" \
    "httpx>=0.27" \
    "supabase>=2.0" \
    "python-dotenv>=1.0"

WORKDIR /app/apps/dashboard
EXPOSE 8501
CMD ["streamlit", "run", "Home.py", "--server.address", "0.0.0.0", "--server.headless", "true"]
