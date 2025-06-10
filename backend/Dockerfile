# Dockerfile

FROM public.ecr.aws/lambda/python:3.11

# Set working directory
WORKDIR /var/task

# Copy app code
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the Lambda handler
CMD ["app.main.handler"]
