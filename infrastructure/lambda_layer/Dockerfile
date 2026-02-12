# Use Amazon Linux 2023 to match Lambda runtime environment
FROM public.ecr.aws/lambda/python:3.12

# Set working directory
WORKDIR /asset

# Copy requirements file
COPY requirements.txt .

# Install dependencies to /asset/python directory (Lambda layer structure)
RUN pip install -r requirements.txt -t /asset/python --no-cache-dir

# Copy shared utilities
COPY python/ /asset/python/

# The output will be in /asset which can be copied out
CMD ["/bin/bash"]
