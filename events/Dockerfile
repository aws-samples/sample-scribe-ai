FROM public.ecr.aws/lambda/python:3.12-arm64

# Set up the directory structure
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements first for better layer caching
COPY ./events/piplock.txt .
RUN pip install --upgrade pip
RUN pip install -r piplock.txt

# Copy the shared directory to the root level
COPY ./shared/ ${LAMBDA_TASK_ROOT}/shared/

# Copy the events directory
COPY ./events/events/ ${LAMBDA_TASK_ROOT}/events/

# Copy the lambda function
COPY ./events/lambda_function.py .

# Command to run
CMD ["lambda_function.lambda_handler"]
