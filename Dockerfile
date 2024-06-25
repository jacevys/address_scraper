FROM python:3.9.13

WORKDIR /tron_2

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "./src/server.py"]

EXPOSE 7777