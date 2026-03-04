FROM --platform=linux/386 i386/debian:bullseye-slim

# Install Mono, Python, and Graphical Support Libraries
RUN apt-get update && apt-get install -y \
    mono-complete \
    python3 \
    xvfb \
    libgdiplus \
    && rm -rf /var/lib/apt/lists/*

ENV MONO_IOMAP=all
WORKDIR /app

COPY ./PAT /app/PAT
COPY ./verifier.py /app/verifier.py

# --- THE CLEANUP ---
# 1. Remove ALL modules except CSP to prevent the "Invalid Image" discovery error
# 2. Ensure naming is exactly what the binary expects (Case-Sensitive Linux)
RUN mkdir -p /app/PAT/Modules_Backup && \
    mv /app/PAT/Modules/CSP /app/PAT/Modules_Backup/ && \
    rm -rf /app/PAT/Modules && \
    mkdir -p /app/PAT/Modules && \
    mv /app/PAT/Modules_Backup/CSP /app/PAT/Modules/CSP

# Fix permissions
RUN chmod +x /app/PAT/PAT3.Console.exe

# Use Xvfb to provide a fake display for the GDI+ initialization
CMD ["xvfb-run", "-a", "python3", "verifier.py"]