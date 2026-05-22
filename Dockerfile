FROM python:3.12-slim

WORKDIR /app

# Install dependencies for Chrome/Chromium and other tools
RUN apt-get update && apt-get install -y \
    gcc g++ libffi-dev \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    libgtk-3-0 libgbm-dev libxshmfence1 \
    wget gnupg \
    curl x11vnc xvfb git \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC
RUN git clone https://github.com/novnc/noVNC /root/noVNC
RUN cd /root/noVNC && npm install
RUN cd /root/noVNC/utils && npm install

# Install Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Install Python backend requirements
COPY web/requirements.txt ./web/
RUN pip install --no-cache-dir -r web/requirements.txt
RUN playwright install chromium
RUN playwright install-deps chromium

# Create non-root user
RUN useradd -m -u 1000 appuser
RUN chown -R appuser:appuser /app /root/noVNC || true

# Copy all code
COPY --chown=appuser:appuser . .

# Install proxy dependency
RUN npm init -y && npm install http-proxy

# Build Next.js frontend
RUN cd web/frontend && npm install && NEXT_PUBLIC_API_URL="" npm run build

# Install VNC social dependencies
RUN cd web && npm install playwright-extra puppeteer-extra-plugin-stealth cloakbrowser playwright-core

# Switch to appuser
USER appuser

EXPOSE 8000

CMD ["bash", "start.sh"]
