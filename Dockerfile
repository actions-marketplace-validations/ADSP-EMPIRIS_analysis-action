FROM python:3.8-slim

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY analysis.py /analysis.py

ENTRYPOINT ["python", "/analysis.py"]