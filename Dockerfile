FROM python:3.12-slim
LABEL author="jsamis"

WORKDIR /src

COPY ./requiremets.txt /src/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /src/requirements.txt

COPY ./app /src/app/

# Default from the Google Cloud Run docs
EXPOSE 8080

CMD ["fastapi", "run" , "app/main.py", "--port", "80"]




