FROM surnet/alpine-python-wkhtmltopdf:3.10.6-0.12.6-full
MAINTAINER Dmitriy Pomazunovskiy <dmitriy.pom0@gmail.com>

WORKDIR /app

RUN apk add gcc libc-dev libffi-dev

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src src

EXPOSE 80

CMD [ "python", "src/main.py" ]
