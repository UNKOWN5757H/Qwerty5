# 1. FIX: Use a supported base image (Debian 11 Bullseye) instead of EOL Buster
FROM python:3.10-slim-bullseye

# 2. Combine RUN commands and clean up apt cache to reduce image size
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Set the working directory
WORKDIR /Qwerty5

# 4. OPTIMIZATION: Copy *only* the requirements file first
COPY requirements.txt .

# 5. OPTIMIZATION: Install requirements
# This step is now cached. It will only re-run if requirements.txt changes.
RUN pip install --no-cache-dir -U pip -r requirements.txt

# 6. OPTIMIZATION: *Now* copy the rest of your bot's code
# This won't break the pip install cache when you just change .py files.
COPY . .

# 7. Set the command to run your bot
CMD ["python", "bot.py"]
