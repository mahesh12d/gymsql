FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

COPY lambda/ ${LAMBDA_TASK_ROOT}/
COPY config/ ${LAMBDA_TASK_ROOT}/config/

CMD ["handler.lambda_handler"]
