ARG PYTHON_VERSION=3.10

FROM python:$PYTHON_VERSION

RUN pip install --no-cache-dir pytest \
                               pylint \
                               pytest-cov \
                               build \
                               setuptools \
                               twine

WORKDIR /github/workspace
