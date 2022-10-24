FROM surnet/alpine-python-wkhtmltopdf:3.10.6-0.12.6-full
MAINTAINER Dmitriy Pomazunovskiy <dmitriy.pom0@gmail.com>

RUN apk add gcc libc-dev libffi-dev

WORKDIR /app

COPY src src
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN ls -la .

EXPOSE 8080

CMD [ "python", "src/main.py" ]
