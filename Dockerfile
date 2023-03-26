FROM python:3.10

RUN pip install --no-cache-dir pytest \
                               pylint \
                               pytest-cov \
                               build \
                               setuptools \
                               twine

WORKDIR /github/workspace
