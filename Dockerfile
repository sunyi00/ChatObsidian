FROM ccr.ccs.tencentyun.com/arksa/baseimage:latest

COPY . /lain/app

USER root

RUN chown -R ark.ark /lain/app

USER ark

ENV PATH=/home/ark/.nvm/versions/node/v18.16.0/bin:/home/ark/.pyenv/shims:/home/ark/.pyenv/bin:$PATH

RUN pip install -U pip wheel && \
    pip install -r /lain/app/pip-req.txt

