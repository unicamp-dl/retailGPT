FROM python:3.10-slim

WORKDIR /app

COPY src/ pyproject.toml poetry.lock /app/

RUN pip install poetry==1.7.1

RUN poetry install --without dev

EXPOSE 8501

CMD ["poetry", "run", "python", "-m", "streamlit", "run", "app.py"]
