FROM python:3.10

RUN pip install --no-cache-dir pytest \
                               pylint \
                               pytest-cov \
                               build \
                               setuptools

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /github/workspace
