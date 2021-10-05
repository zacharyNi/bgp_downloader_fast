FROM python:3.8.10
WORKDIR /app
COPY requestments.txt requestments.txt
RUN pip3 install -r requestments.txt
COPY . .
CMD ["python3","download.py","-c","all","-d","ribs","-s","2020-01-01-00:01","-e","2020-12-31-23:59"]