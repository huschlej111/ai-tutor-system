FROM public.ecr.aws/lambda/python:3.12

# Copy model files from project root
COPY final_similarity_model/ /opt/ml/model/

# Install PyTorch CPU-only first
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies from PyPI
COPY lambda/answer-evaluator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Lambda function
COPY lambda/answer-evaluator/lambda_function.py ${LAMBDA_TASK_ROOT}/

# Set handler
CMD ["lambda_function.handler"]
